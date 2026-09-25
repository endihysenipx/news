import type { Metadata } from "next"
import { Toaster } from "sonner"
import { AuthProvider } from "@/lib/auth"
import { ConfirmDialogProvider } from "@/components/providers/confirm-dialog-provider"
import "./globals.css"

export const metadata: Metadata = { title: "News Intelligence", description: "Independent business intelligence workspace" }

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body className="font-sans"><AuthProvider><ConfirmDialogProvider>{children}<Toaster position="bottom-right" richColors /></ConfirmDialogProvider></AuthProvider></body></html>
}
