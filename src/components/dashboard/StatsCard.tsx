import { ReactNode } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export type Trend = "up" | "down" | "neutral";

interface StatsCardProps {
  title: string;
  value: string | number;
  trend: Trend;
  trendValue: string;
  icon: ReactNode;
  description?: string;
  variant?: "default" | "success" | "warning" | "danger";
}

export const StatsCard = ({ 
  title, 
  value, 
  trend, 
  trendValue, 
  icon, 
  description,
  variant = "default" 
}: StatsCardProps) => {
  const TrendIcon = trend === "up" ? ArrowUpRight : trend === "down" ? ArrowDownRight : Minus;
  const trendColor = trend === "up" ? "text-green-600" : trend === "down" ? "text-red-600" : "text-muted-foreground";
  const trendBg = trend === "up" ? "bg-green-50" : trend === "down" ? "bg-red-50" : "bg-muted/20";

  const getVariantStyles = () => {
    switch (variant) {
      case "success":
        return "border-green-200 bg-gradient-to-br from-green-50 to-green-100/50";
      case "warning":
        return "border-amber-200 bg-gradient-to-br from-amber-50 to-amber-100/50";
      case "danger":
        return "border-red-200 bg-gradient-to-br from-red-50 to-red-100/50";
      default:
        return "bg-gradient-to-br from-card to-muted/20";
    }
  };

  const getIconStyles = () => {
    switch (variant) {
      case "success":
        return "text-green-600 bg-green-100";
      case "warning":
        return "text-amber-600 bg-amber-100";
      case "danger":
        return "text-red-600 bg-red-100";
      default:
        return "text-primary bg-primary/10";
    }
  };

  return (
    <Card className={`hover-scale transition-all duration-200 hover:shadow-lg border ${getVariantStyles()}`}>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-sm font-medium text-muted-foreground tracking-tight">
          {title}
        </CardTitle>
        <div className={`p-2 rounded-lg ${getIconStyles()}`}>
          {icon}
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="space-y-3">
          <div className="text-3xl font-bold tracking-tight text-foreground">
            {value}
          </div>
          
          <div className="flex items-center justify-between">
            <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium ${trendBg} ${trendColor}`}>
              <TrendIcon className="h-3 w-3" />
              <span>{trendValue}</span>
            </div>
            
            {description && (
              <p className="text-xs text-muted-foreground hidden sm:block">
                {description}
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};