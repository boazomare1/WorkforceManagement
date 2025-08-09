import { PropsWithChildren } from "react";
import { Outlet, Link } from "react-router-dom";
import { SidebarProvider, SidebarTrigger, SidebarInset } from "@/components/ui/sidebar";
import { AppSidebar } from "./AppSidebar";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";

export default function AppLayout({ children }: PropsWithChildren) {
  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <AppSidebar />
        <SidebarInset className="flex flex-col flex-1">
          <header className="h-16 flex items-center border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-40 px-6">
            <div className="flex items-center gap-4 flex-1">
              <SidebarTrigger className="h-8 w-8" />
              <div className="flex items-center gap-3">
                <Link to="/dashboard" className="font-semibold tracking-tight text-lg hover:text-primary transition-colors">
                  FlairChef Suite
                </Link>
                <div className="h-4 w-px bg-border" />
                <span className="text-sm text-muted-foreground">Restaurant Management</span>
              </div>
              <div className="ml-auto flex items-center gap-3">
                <div className="hidden sm:flex items-center gap-2 text-sm text-muted-foreground">
                  <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                  <span>System Online</span>
                </div>
                <Link to="/pos">
                  <Button variant="hero" size="sm" className="hover-scale shadow-sm">
                    <Plus className="h-4 w-4 mr-1.5" />
                    New Order
                  </Button>
                </Link>
              </div>
            </div>
          </header>

          <main className="flex-1 px-6 py-8 bg-background">
            {children ?? <Outlet />}
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
}