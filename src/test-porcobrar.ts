/**
 * Script de validación de la integración PorCobrar (createInvoice / payment links).
 *
 * Ejecutar:  npm run test:porcobrar
 * Requiere: PORCOBRAR_ACCESS_TOKEN (y opcional PORCOBRAR_API_URL) en .env o .env.local.
 * Si createInvoice falla, el test imprime endpoint, body y response en un bloque "Para enviar a soporte PorCobrar" (copia y envía a soporte).
 */
import { config } from "dotenv";
import { randomUUID } from "crypto";
config();
config({ path: ".env.local" });

const PORCOBRAR_API_URL = process.env.PORCOBRAR_API_URL || "https://api.porcobrar.com";
const PORCOBRAR_ACCESS_TOKEN = process.env.PORCOBRAR_ACCESS_TOKEN;

async function main(): Promise<void> {
    console.log("=== Validación integración PorCobrar ===\n");

    if (PORCOBRAR_API_URL.includes("app.porcobrar") && !PORCOBRAR_API_URL.includes("api.porcobrar")) {
        console.error("❌ PORCOBRAR_API_URL apunta a la app (frontend), no a la API.");
        console.error("   Actual: " + PORCOBRAR_API_URL);
        console.error("   Usa la API: https://stage.api.porcobrar.com (stage) o https://api.porcobrar.com (prod)");
        process.exit(1);
    }

    console.log("1. Configuración:");
    console.log(`   PORCOBRAR_API_URL: ${PORCOBRAR_API_URL}`);
    if (PORCOBRAR_ACCESS_TOKEN) {
        const len = PORCOBRAR_ACCESS_TOKEN.length;
        const visible = len <= 40 ? PORCOBRAR_ACCESS_TOKEN : `${PORCOBRAR_ACCESS_TOKEN.slice(0, 20)}...${PORCOBRAR_ACCESS_TOKEN.slice(-15)}`;
        console.log(`   PORCOBRAR_ACCESS_TOKEN: ${visible} (${len} chars)`);
    } else {
        console.log(`   PORCOBRAR_ACCESS_TOKEN: [MISSING]`);
    }

    if (!PORCOBRAR_ACCESS_TOKEN || PORCOBRAR_ACCESS_TOKEN === "your_token_here") {
        console.error("\n❌ Falta PORCOBRAR_ACCESS_TOKEN. Configúralo en .env o .env.local");
        process.exit(1);
    }

    const contrato = process.env.TEST_CONTRACT || "523160";
    const total_amount = 1.0;
    const customer_name = "Prueba Validación CEA Agent " + contrato + " " + Date.now();
    const customer_rfc = "XAXX010101000";

    // Rutas candidatas (la doc v2 no expone el path exacto; 400 = ruta existe, 404 = no existe)
    const candidates = [
        "/v1/invoice/invoice",
        "/v2/invoice",
        "/v2/invoices",
        "/api/v2/invoice",
        "/api/v2/invoices"
    ];
    const invoicePath = process.env.PORCOBRAR_INVOICE_PATH || candidates[0];
    if (!process.env.PORCOBRAR_INVOICE_PATH) {
        console.log("\n2. Probando rutas (400 = ruta existe, body inválido; 404 = ruta no existe):");
        const minimalBody = JSON.stringify({ customer: {}, invoice: {} });
        for (const path of candidates) {
            try {
                const r = await fetch(`${PORCOBRAR_API_URL}${path}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json", Authorization: `Bearer ${PORCOBRAR_ACCESS_TOKEN}` },
                    body: minimalBody,
                    signal: AbortSignal.timeout(5000)
                });
                console.log(`   ${path} → ${r.status}`);
            } catch (e) {
                console.log(`   ${path} → error: ${(e as Error).message}`);
            }
        }
        console.log("   Usando: " + invoicePath + " (override con PORCOBRAR_INVOICE_PATH si hace falta)\n");
    }
    console.log("3. Crear cliente (POST /v1/customer) y luego factura (POST /v1/invoice/invoice)");
    console.log("   contrato=" + contrato + ", total_amount=" + total_amount + ", customer_name=" + customer_name);

    let customerUUID: string;
    const createCustomerRes = await fetch(`${PORCOBRAR_API_URL}/v1/customer`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${PORCOBRAR_ACCESS_TOKEN}`
        },
        body: JSON.stringify({
            name: customer_name,
            legal_name: customer_name,
            tax_profile: customer_rfc,
            tax_regime: 616,
            agreement: { payment_term: 30 }
        }),
        signal: AbortSignal.timeout(10000)
    });
    const customerBody = await createCustomerRes.text();
    if (!createCustomerRes.ok) {
        console.log("\n4. Error creando cliente:");
        console.log("   Status:", createCustomerRes.status, createCustomerRes.statusText);
        console.log("   Body:", customerBody.slice(0, 500));
        process.exit(1);
    }
    const customerData = JSON.parse(customerBody);
    customerUUID = customerData?.data?.uuid;
    if (!customerUUID) {
        console.log("\n4. Respuesta de cliente sin data.uuid:", customerBody.slice(0, 300));
        process.exit(1);
    }
    console.log("   Cliente creado: uuid=" + customerUUID);

    const itemsRes = await fetch(`${PORCOBRAR_API_URL}/v1/item`, {
        method: "GET",
        headers: { Authorization: `Bearer ${PORCOBRAR_ACCESS_TOKEN}` },
        signal: AbortSignal.timeout(5000)
    });
    let itemIdFromCatalog: number | undefined;
    if (itemsRes.ok) {
        const itemsData = await itemsRes.json();
        const raw = itemsData?.data ?? itemsData;
        const items = Array.isArray(raw) ? raw : raw?.items ?? [];
        if (items.length > 0 && items[0].id != null) {
            itemIdFromCatalog = items[0].id;
            console.log("   Catálogo items: " + items.length + " (usando id=" + itemIdFromCatalog + ")");
        } else if (items.length > 0) {
            console.log("   Catálogo items: " + items.length + ", primer ítem keys: " + Object.keys(items[0]).join(","));
        }
    } else {
        console.log("   GET /v1/item status: " + itemsRes.status);
    }

    const now = Math.floor(Date.now() / 1000);
    const dueDate = now + 30 * 24 * 60 * 60;
    const subtotal = Number((total_amount / 1.16).toFixed(2));
    const tax = Number((total_amount - subtotal).toFixed(2));
    const itemSubtotal = subtotal;
    const itemTax = tax;
    const itemTotal = total_amount;
    const taxAmount = tax;
    const taxBase = subtotal;

    const requestBody = {
        customer: {
            id: customerUUID,
            legal_name: customer_name,
            tax_profile: customer_rfc
        },
        invoice: {
            type: "invoice",
            currency: "MXN",
            currency_rate: 1,
            discount: 0,
            issue_date: now,
            due_date: dueDate,
            subtotal,
            tax,
            total: Number(total_amount.toFixed(2)),
            purchase_order: `CEA-${contrato}`,
            identifier: `CEA-${contrato}`.slice(0, 64),
            notes: `Pago servicio agua. Contrato: ${contrato}`,
            comment: "",
            detailed: false,
            observation: "",
            terms: 30,
            origin: "api",
            send_email: false,
            attributes: {
                cfdi_self_invoicing: false,
                cfdi_seal_version: "4.0",
                cfdi_payment_method: "PUE",
                cfdi_payment_type: 1,
                cfdi_payment_conditions: 30
            },
            items: [
                {
                    ...(itemIdFromCatalog != null && { id: itemIdFromCatalog }),
                    attributes: { cfdi_code: "90111700", cfdi_unit_code: "E48" },
                    description: `Servicio de agua - Contrato ${contrato}`,
                    quantity: 1,
                    unit_id: 3,
                    price: itemSubtotal,
                    unit_price: itemSubtotal,
                    subtotal: itemSubtotal,
                    typeDiscount: "percent",
                    discount: 0,
                    tax: itemTax,
                    total: itemTotal,
                    tax_object: "02",
                    taxes: [
                        {
                            code: "002",
                            name: "IVA 16%",
                            rate: 0.16,
                            amount: 0.16,
                            base: taxBase,
                            total: taxAmount,
                            is_percentage: 1,
                            added: 1
                        }
                    ]
                }
            ]
        }
    };

    const invoiceUrl = `${PORCOBRAR_API_URL}${invoicePath}`;

    try {
        const response = await fetch(invoiceUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${PORCOBRAR_ACCESS_TOKEN}`
            },
            body: JSON.stringify(requestBody),
            signal: AbortSignal.timeout(30000)
        });

        const bodyText = await response.text();

        console.log("\n5. Respuesta API (createInvoice):");
        console.log(`   Status: ${response.status} ${response.statusText}`);

        if (!response.ok) {
            let errDetail: string;
            try {
                const errJson = JSON.parse(bodyText);
                errDetail = errJson.message ?? errJson.error ?? errJson.detail ?? bodyText;
            } catch {
                errDetail = bodyText || `HTTP ${response.status}`;
            }
            console.log(`   Error: ${errDetail}`);
            console.log("\n--- Para enviar a soporte PorCobrar ---");
            console.log("Endpoint llamado: POST " + invoiceUrl);
            console.log("Request body:\n" + JSON.stringify(requestBody, null, 2));
            console.log("Response status: " + response.status + " " + response.statusText);
            console.log("Response body:\n" + (bodyText.length > 2000 ? bodyText.slice(0, 2000) + "\n... (truncado)" : bodyText));
            console.log("--- Fin ---\n");
            if (bodyText.includes('"code":102')) {
                console.log("   💡 Código 102 = 'Required param missing'. Envía el bloque anterior a soporte.");
            }
            console.log("❌ La integración falló. Revisa token, URL y formato del request (v2 docs).");
            process.exit(1);
        }

        const result = JSON.parse(bodyText);
        const paymentLink = result.data?.payment_link;
        const folio = result.data?.folio ?? result.data?.uuid;

        if (!paymentLink) {
            console.log("   Respuesta (sin payment_link):", JSON.stringify(result, null, 2).slice(0, 500));
            console.log("\n❌ La API no devolvió payment_link. Revisa el contrato de la API v1/v2.");
            process.exit(1);
        }

        console.log("   ✅ success: true");
        console.log(`   payment_link: ${paymentLink}`);
        console.log(`   folio: ${folio ?? "N/A"}`);
        console.log(`   total: ${total_amount}`);
        console.log("\n✅ Integración PorCobrar validada correctamente.");
        process.exit(0);
    } catch (err) {
        console.error("\nError ejecutando validación:", err);
        process.exit(1);
    }
}

main();
