"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function AgentBuilderLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { token, refreshUser } = useAuth();

  useEffect(() => {
    if (!token) {
      router.push("/auth/login");
    } else {
      refreshUser();
    }
  }, [token, router, refreshUser]);

  if (!token) {
    return null;
  }

  return (
    <div className="h-screen bg-[#0a0a0f] text-white overflow-hidden">
      {children}
    </div>
  );
}
