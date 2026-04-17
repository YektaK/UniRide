
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Sidebar,
  SidebarHeader,
  SidebarContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarFooter,
} from "@/components/ui/sidebar";
import { useAuth } from "@/hooks/use-auth";
import {
  LayoutDashboard,
  CalendarDays,
  ClipboardList,
  User,
  Bus,
  Users,
  Settings,
  MapPin,
  ShieldAlert,
  LogOut,
  HelpingHand,
  ListChecks,
  FilePenLine,
  BarChartHorizontal, // Icon for Reports
  Navigation, // Icon for Driver navigation
  Route, // Icon for Driver routes
  Cpu, // Icon for Algorithms
  FlaskConical, // Icon for Sandbox
  BarChart3, // Icon for Benchmark
} from "lucide-react";
import { Button } from "../ui/button";

const commonMenuItems = [
  { href: "/dashboard", label: "Kontrol Paneli", icon: LayoutDashboard },
  { href: "/profile", label: "Profilim", icon: User },
];

const studentMenuItems = [
  { href: "/schedule", label: "Ders Programım", icon: CalendarDays },
  { href: "/request-ride", label: "Servis Talebi", icon: ClipboardList },
  { href: "/ride-history", label: "Taleplerim", icon: ListChecks },
  { href: "/track-ride", label: "Servis Takibi", icon: MapPin },
];

const adminMenuItems = [
  { href: "/admin/vehicles", label: "Araç Yönetimi", icon: Bus },
  { href: "/admin/users", label: "Kullanıcı Yönetimi", icon: Users },
  { href: "/admin/schedules", label: "Ders Programları", icon: FilePenLine },
  { href: "/admin/ride-requests", label: "Servis Talepleri", icon: ShieldAlert },
  { href: "/admin/drivers", label: "Şoför Görevlendirmeleri", icon: Users },
  { href: "/admin/vehicle-planning", label: "Araç Planlama", icon: Route },
  { href: "/admin/sandbox", label: "IE Sandbox", icon: FlaskConical },
  { href: "/admin/compare", label: "Algoritma Karşılaştırma", icon: Cpu },
  { href: "/admin/benchmark", label: "Benchmark Suite", icon: BarChart3 },
  { href: "/admin/route-test", label: "Rota Testi", icon: Navigation },
  { href: "/admin/reports", label: "Raporlar", icon: BarChartHorizontal },
  { href: "/admin/settings", label: "Ayarlar", icon: Settings },
];

const driverMenuItems = [
  { href: "/driver/assignments", label: "Görevlerim", icon: Route },
  { href: "/driver/navigation", label: "Navigasyon", icon: Navigation },
  { href: "/driver/history", label: "Geçmiş Seferler", icon: ListChecks },
];

export default function AppSidebar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  if (!user) return null;

  const getMenuItems = () => {
    switch (user.role) {
      case "admin":
        return [...commonMenuItems, ...adminMenuItems];
      case "driver":
        return [...commonMenuItems, ...driverMenuItems];
      default:
        return [...commonMenuItems, ...studentMenuItems];
    }
  };

  const menuItems = getMenuItems();

  return (
    <Sidebar collapsible="icon" variant="sidebar" side="left" className="border-r">
      <SidebarHeader className="p-4 justify-center">
        <Link href="/dashboard">
          <div className="flex items-center gap-2 group-data-[collapsible=icon]:hidden">
            <HelpingHand className="h-8 w-8 text-primary" />
            <h1 className="text-lg font-semibold text-foreground">UniRide</h1>
          </div>
          <HelpingHand className="h-8 w-8 text-primary hidden group-data-[collapsible=icon]:block" />
        </Link>
      </SidebarHeader>
      <SidebarContent className="flex-grow p-2">
        <SidebarMenu>
          {menuItems.map((item) => (
            <SidebarMenuItem key={item.href}>
              <SidebarMenuButton
                asChild
                isActive={pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href))}
                tooltip={{ children: item.label, side: "right", align: "center" }}
                aria-label={item.label}
              >
                <Link href={item.href}>
                  <item.icon />
                  <span>{item.label}</span>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarContent>
      <SidebarFooter className="p-4 border-t">
        <Button variant="ghost" onClick={logout} className="w-full justify-start group-data-[collapsible=icon]:justify-center">
          <LogOut className="mr-2 group-data-[collapsible=icon]:mr-0 h-4 w-4" />
          <span className="group-data-[collapsible=icon]:hidden">Çıkış Yap</span>
        </Button>
      </SidebarFooter>
    </Sidebar>
  );
}

