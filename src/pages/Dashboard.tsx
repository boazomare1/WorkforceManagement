import { SEO } from "@/components/common/SEO";
import { StatsCard } from "@/components/dashboard/StatsCard";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { 
  DollarSign, 
  ShoppingBag, 
  UserCheck, 
  Map, 
  Plus, 
  TrendingUp,
  Clock,
  Star,
  Users,
  ChefHat,
  Coffee,
  Activity
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell
} from "recharts";

const salesData = [
  { name: "09:00", sales: 320, orders: 12 },
  { name: "10:00", sales: 480, orders: 18 },
  { name: "11:00", sales: 390, orders: 15 },
  { name: "12:00", sales: 820, orders: 35 },
  { name: "13:00", sales: 760, orders: 28 },
  { name: "14:00", sales: 640, orders: 22 },
  { name: "15:00", sales: 900, orders: 32 },
  { name: "16:00", sales: 650, orders: 24 },
  { name: "17:00", sales: 750, orders: 27 },
];

const topItems = [
  { name: "Caesar Salad", orders: 45, revenue: 675 },
  { name: "Grilled Salmon", orders: 32, revenue: 896 },
  { name: "Ribeye Steak", orders: 28, revenue: 1120 },
  { name: "Pasta Carbonara", orders: 38, revenue: 532 },
];

const recentOrders = [
  { id: "#1234", table: "A-12", items: 3, total: 67.50, status: "Preparing", time: "2 min ago" },
  { id: "#1235", table: "B-08", items: 5, total: 124.00, status: "Ready", time: "5 min ago" },
  { id: "#1236", table: "C-15", items: 2, total: 45.20, status: "Served", time: "8 min ago" },
  { id: "#1237", table: "A-05", items: 4, total: 89.75, status: "Preparing", time: "10 min ago" },
];

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

export default function Dashboard() {
  return (
    <main className="space-y-8">
      <SEO
        title="Restaurant Dashboard - FlairChef Suite"
        description="Real-time overview of sales, orders, staff attendance, and table occupancy."
        canonical="/dashboard"
      />

      {/* Header Section */}
      <header className="space-y-2">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text">
              Restaurant Dashboard
            </h1>
            <p className="text-muted-foreground">
              Live insights and real-time operations overview
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant="outline" className="px-3 py-1">
              <Activity className="h-3 w-3 mr-1.5" />
              Live
            </Badge>
            <Badge variant="secondary" className="px-3 py-1">
              Today: {new Date().toLocaleDateString()}
            </Badge>
          </div>
        </div>
      </header>

      {/* Stats Cards */}
      <section aria-label="Key metrics" className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
        <StatsCard
          title="Revenue Today"
          value="$4,820"
          trend="up"
          trendValue="+12% vs yesterday"
          icon={<DollarSign className="h-5 w-5" />}
          description="Target: $5,000"
          variant="success"
        />
        <StatsCard
          title="Orders Completed"
          value={186}
          trend="up"
          trendValue="+8% vs yesterday"
          icon={<ShoppingBag className="h-5 w-5" />}
          description="Avg order: $25.90"
          variant="default"
        />
        <StatsCard
          title="Staff Present"
          value="18/22"
          trend="neutral"
          trendValue="On schedule"
          icon={<UserCheck className="h-5 w-5" />}
          description="All shifts covered"
          variant="default"
        />
        <StatsCard
          title="Table Occupancy"
          value="73%"
          trend="down"
          trendValue="-3% vs yesterday"
          icon={<Map className="h-5 w-5" />}
          description="18 of 24 tables"
          variant="warning"
        />
      </section>

      {/* Main Content Grid */}
      <section className="grid gap-6 lg:grid-cols-12">
        {/* Sales Chart - Large */}
        <Card className="lg:col-span-8">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-xl">Sales Performance</CardTitle>
                <p className="text-sm text-muted-foreground mt-1">
                  Hourly revenue and order tracking
                </p>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded bg-primary"></div>
                  <span>Sales ($)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded bg-green-500"></div>
                  <span>Orders</span>
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={salesData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorSales" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                <XAxis 
                  dataKey="name" 
                  tick={{ fontSize: 12 }} 
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis 
                  tick={{ fontSize: 12 }} 
                  tickLine={false}
                  axisLine={false}
                />
                <RechartsTooltip 
                  contentStyle={{ 
                    borderRadius: 8, 
                    border: 'none',
                    boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                  }} 
                />
                <Area 
                  type="monotone" 
                  dataKey="sales" 
                  stroke="hsl(var(--primary))" 
                  fillOpacity={1} 
                  fill="url(#colorSales)"
                  strokeWidth={2}
                />
                <Line 
                  type="monotone" 
                  dataKey="orders" 
                  stroke="#10b981" 
                  strokeWidth={2} 
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Quick Actions & Status */}
        <div className="lg:col-span-4 space-y-6">
          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button variant="hero" className="w-full justify-start hover-scale" size="lg">
                <Plus className="h-4 w-4 mr-2" />
                New Order
              </Button>
              <div className="grid grid-cols-2 gap-3">
                <Button variant="outline" className="justify-start">
                  <Users className="h-4 w-4 mr-2" />
                  Staff
                </Button>
                <Button variant="outline" className="justify-start">
                  <ChefHat className="h-4 w-4 mr-2" />
                  Kitchen
                </Button>
                <Button variant="outline" className="justify-start">
                  <Map className="h-4 w-4 mr-2" />
                  Tables
                </Button>
                <Button variant="outline" className="justify-start">
                  <Coffee className="h-4 w-4 mr-2" />
                  Menu
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Table Status */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Table Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between text-sm">
                  <span>Occupied</span>
                  <span className="font-medium">18/24</span>
                </div>
                <Progress value={75} className="h-2" />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Average turn time: 45 min</span>
                  <span>Peak hours</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Top Items */}
        <Card className="lg:col-span-6">
          <CardHeader>
            <CardTitle className="text-lg">Top Selling Items</CardTitle>
            <p className="text-sm text-muted-foreground">Most popular dishes today</p>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {topItems.map((item, index) => (
                <div key={item.name} className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 text-primary font-semibold text-sm">
                      {index + 1}
                    </div>
                    <div>
                      <p className="font-medium">{item.name}</p>
                      <p className="text-sm text-muted-foreground">{item.orders} orders</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold">${item.revenue}</p>
                    <p className="text-xs text-muted-foreground">revenue</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Recent Orders */}
        <Card className="lg:col-span-6">
          <CardHeader>
            <CardTitle className="text-lg">Recent Orders</CardTitle>
            <p className="text-sm text-muted-foreground">Latest customer orders</p>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentOrders.map((order) => (
                <div key={order.id} className="flex items-center justify-between p-3 rounded-lg border">
                  <div className="flex items-center gap-3">
                    <div>
                      <p className="font-medium">{order.id}</p>
                      <p className="text-sm text-muted-foreground">Table {order.table}</p>
                    </div>
                  </div>
                  <div className="text-center">
                    <p className="text-sm">{order.items} items</p>
                    <p className="text-xs text-muted-foreground">${order.total}</p>
                  </div>
                  <div className="text-right">
                    <Badge 
                      variant={order.status === 'Ready' ? 'default' : order.status === 'Served' ? 'secondary' : 'outline'}
                      className="mb-1"
                    >
                      {order.status}
                    </Badge>
                    <p className="text-xs text-muted-foreground">{order.time}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}