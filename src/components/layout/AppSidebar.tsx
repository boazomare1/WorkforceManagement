import { NavLink, useLocation } from "react-router-dom";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
  SidebarHeader,
  SidebarFooter,
} from "@/components/ui/sidebar";
import {
  LayoutDashboard,
  ShoppingCart,
  Users,
  Table as TableIcon,
  ChefHat,
  UsersRound,
  Boxes,
  LineChart,
  Settings,
  LogOut,
  Crown,
  DollarSign,
} from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

const mainItems = [
  { 
    title: "Dashboard", 
    url: "/dashboard", 
    icon: LayoutDashboard,
    badge: null,
    description: "Overview & insights",
    color: "text-blue-600"
  },
  { 
    title: "POS Terminal", 
    url: "/pos", 
    icon: ShoppingCart,
    badge: "Live",
    badgeVariant: "default" as const,
    description: "Point of sale",
    color: "text-green-600"
  },
  { 
    title: "Tables", 
    url: "/tables", 
    icon: TableIcon,
    badge: "18/24",
    badgeVariant: "secondary" as const,
    description: "Table management",
    color: "text-purple-600"
  },
  { 
    title: "Kitchen", 
    url: "/kitchen", 
    icon: ChefHat,
    badge: "12",
    badgeVariant: "destructive" as const,
    description: "Order display",
    color: "text-orange-600"
  },
];

const managementItems = [
  { 
    title: "Staff", 
    url: "/staff", 
    icon: Users,
    badge: null,
    description: "Team management",
    color: "text-indigo-600"
  },
  { 
    title: "Customers", 
    url: "/customers", 
    icon: UsersRound,
    badge: null,
    description: "Customer data",
    color: "text-teal-600"
  },
  { 
    title: "Inventory", 
    url: "/inventory", 
    icon: Boxes,
    badge: "Low: 5",
    badgeVariant: "outline" as const,
    description: "Stock levels",
    color: "text-amber-600"
  },
];

const analyticsItems = [
  { 
    title: "Analytics", 
    url: "/analytics", 
    icon: LineChart,
    badge: null,
    description: "Reports & trends",
    color: "text-rose-600"
  },
];

export function AppSidebar() {
  const { state } = useSidebar();
  const collapsed = state === "collapsed";
  const location = useLocation();
  const currentPath = location.pathname;

  const isActive = (path: string) => currentPath === path;

  const renderMenuItem = (item: typeof mainItems[0]) => (
    <SidebarMenuItem key={item.title}>
      <SidebarMenuButton asChild isActive={isActive(item.url)} className="h-12">
        <NavLink 
          to={item.url} 
          end 
          className="flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200 hover:scale-[1.02] group"
        >
          <div className={`p-2 rounded-md ${isActive(item.url) ? 'bg-primary/10' : 'bg-muted/50 group-hover:bg-muted'} transition-colors`}>
            <item.icon className={`h-4 w-4 ${isActive(item.url) ? 'text-primary' : item.color}`} />
          </div>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <span className="font-medium text-sm truncate">{item.title}</span>
                {item.badge && (
                  <Badge variant={item.badgeVariant || "secondary"} className="ml-2 text-xs px-1.5 py-0.5">
                    {item.badge}
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground truncate">{item.description}</p>
            </div>
          )}
        </NavLink>
      </SidebarMenuButton>
    </SidebarMenuItem>
  );

  return (
    <Sidebar className={collapsed ? "w-16" : "w-72"} variant="floating">
      <SidebarHeader className="px-4 py-6">
        {!collapsed ? (
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-primary to-primary/70 rounded-lg">
              <Crown className="h-5 w-5 text-primary-foreground" />
            </div>
            <div>
              <h2 className="font-semibold text-sm">FlairChef Suite</h2>
              <p className="text-xs text-muted-foreground">Restaurant Pro</p>
            </div>
          </div>
        ) : (
          <div className="flex justify-center">
            <div className="p-2 bg-gradient-to-br from-primary to-primary/70 rounded-lg">
              <Crown className="h-5 w-5 text-primary-foreground" />
            </div>
          </div>
        )}
      </SidebarHeader>

      <SidebarContent className="px-3">
        {/* Operations Section */}
        <SidebarGroup>
          <SidebarGroupLabel className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-2">
            {collapsed ? "•••" : "Operations"}
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="space-y-1">
              {mainItems.map(renderMenuItem)}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <Separator className="my-4" />

        {/* Management Section */}
        <SidebarGroup>
          <SidebarGroupLabel className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-2">
            {collapsed ? "•••" : "Management"}
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="space-y-1">
              {managementItems.map(renderMenuItem)}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <Separator className="my-4" />

        {/* Analytics Section */}
        <SidebarGroup>
          <SidebarGroupLabel className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-2">
            {collapsed ? "•••" : "Insights"}
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="space-y-1">
              {analyticsItems.map(renderMenuItem)}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="px-4 py-4 border-t">
        {!collapsed ? (
          <div className="space-y-4">
            {/* User Profile */}
            <div className="flex items-center gap-3">
              <Avatar className="h-8 w-8">
                <AvatarImage src="/avatars/owner.jpg" />
                <AvatarFallback className="bg-primary/10 text-primary font-semibold text-sm">
                  BO
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">Boaz Omare</p>
                <p className="text-xs text-muted-foreground">Restaurant Owner</p>
              </div>
            </div>

            {/* Quick Stats */}
            <div className="bg-muted/30 rounded-lg p-3 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Today's Revenue</span>
                <span className="font-semibold text-green-600">$4,820</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Active Orders</span>
                <span className="font-semibold">12</span>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" className="flex-1 h-8">
                <Settings className="h-3 w-3" />
              </Button>
              <Button variant="ghost" size="sm" className="flex-1 h-8">
                <LogOut className="h-3 w-3" />
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            <Avatar className="h-8 w-8 mx-auto">
              <AvatarFallback className="bg-primary/10 text-primary font-semibold text-sm">
                BO
              </AvatarFallback>
            </Avatar>
            <div className="flex flex-col gap-1">
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                <Settings className="h-3 w-3" />
              </Button>
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                <LogOut className="h-3 w-3" />
              </Button>
            </div>
          </div>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}