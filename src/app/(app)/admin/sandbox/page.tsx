"use client";

/**
 * Sandbox Mode Page - IE Fine-tune Interface
 * EndÃ¼stri MÃ¼hendisliÄŸi Sandbox Modu
 * 
 * Ã–zellikler:
 * - TanÄ±mlÄ± araÃ§larÄ±n seÃ§imi ve konfigÃ¼rasyonu
 * - Ã–zel araÃ§ kapasiteleri ile "what-if" senaryolarÄ±
 * - IE analizi ve optimizasyon
 * - Senaryo kaydetme/yÃ¼kleme
 */

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from 'next-intl';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Checkbox } from "@/components/ui/checkbox";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { adminApi } from "@/lib/admin-api";
import {
  FlaskConical,
  Truck,
  Users,
  Clock,
  Calculator,
  Plus,
  Trash2,
  Save,
  Play,
  Settings2,
  AlertCircle,
  CheckCircle2,
  BarChart3,
} from "lucide-react";
import { IEDashboard } from "@/components/admin/ie-dashboard";
import type { Vehicle } from "@/types";
import type { IEResponseData, VehicleConfig } from "@/types/ie-resource";

// Default vehicle templates
const VEHICLE_TEMPLATES = {
  minibus: { swCapacity: 4, soCapacity: 5, cooldownMinutes: 10 },
  bus: { swCapacity: 8, soCapacity: 15, cooldownMinutes: 15 },
  van: { swCapacity: 2, soCapacity: 3, cooldownMinutes: 10 },
};

// Monotonic module-scope counter for sandbox vehicle ids â€” avoids
// Date.now()/Math.random() in component code (react-hooks/purity)
let sandboxVehicleSeq = 0;
const nextSandboxVehicleId = () => `sb-${++sandboxVehicleSeq}`;

interface SandboxVehicle extends VehicleConfig {
  id: string;
  name: string;
  source: "existing" | "custom";
  originalId?: string; // For existing vehicles
}

interface SandboxScenario {
  id: string;
  name: string;
  vehicles: SandboxVehicle[];
  studentIds: string[];
  timeWindowMinutes: number;
  createdAt: string;
}

export default function SandboxPage() {
  const t = useTranslations('page.admin.sandbox');
  const tc = useTranslations('common');
  const { toast } = useToast();
  
  // Data states
  const [existingVehicles, setExistingVehicles] = useState<Vehicle[]>([]);
  const [students, setStudents] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Sandbox configuration
  const [sandboxVehicles, setSandboxVehicles] = useState<SandboxVehicle[]>([]);
  const [selectedStudentIds, setSelectedStudentIds] = useState<string[]>([]);
  const [timeWindowMinutes, setTimeWindowMinutes] = useState(0);
  
  // Results
  const [ieData, setIeData] = useState<IEResponseData | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);
  
  // Scenarios
  const [savedScenarios, setSavedScenarios] = useState<SandboxScenario[]>([]);
  const [scenarioName, setScenarioName] = useState("");
  const [activeTab, setActiveTab] = useState("configure");

  // Load initial data
  const loadData = async () => {
    setIsLoading(true);
    try {
      // Load vehicles
      const vehiclesResponse = await adminApi.vehicles.getAll();
      const vehicles = Array.isArray(vehiclesResponse) 
        ? vehiclesResponse 
        : vehiclesResponse.data || [];
      
      const convertedVehicles = vehicles.map((v: any) => ({
        id: v.id,
        name: v.name,
        type: v.type,
        plateNumber: v.plate_number,
        wheelchairCapacity: v.wheelchair_capacity,
        seatingCapacity: v.seating_capacity,
        cooldownMinutes: v.cooldown_minutes ?? 10,
        status: v.status,
      }));
      
      setExistingVehicles(convertedVehicles);
      
      // Load students
      const usersResponse = await adminApi.users.getAll(1, 100);
      const usersArray = Array.isArray(usersResponse) 
        ? usersResponse 
        : usersResponse.data || [];
      const studentUsers = usersArray.filter((u: any) => u.role === "student");
      setStudents(studentUsers);
      
    } catch (error) {
      console.error("Error loading data:", error);
      toast({
        title: tc('error'),
        description: tc('error'),
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const loadSavedScenarios = () => {
    const saved = localStorage.getItem("uniride_sandbox_scenarios");
    if (saved) {
      try {
        setSavedScenarios(JSON.parse(saved));
      } catch (e) {
        console.error("Error loading scenarios:", e);
      }
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch-on-mount initial data load; loading flag flips synchronously. Upstream fix: data-fetching framework.
    loadData();
    loadSavedScenarios();
  }, []);

  const saveScenarios = (scenarios: SandboxScenario[]) => {
    localStorage.setItem("uniride_sandbox_scenarios", JSON.stringify(scenarios));
    setSavedScenarios(scenarios);
  };

  // Add vehicle from existing fleet
  const addExistingVehicle = (vehicle: Vehicle) => {
    const sandboxVehicle: SandboxVehicle = {
      id: nextSandboxVehicleId(),
      name: vehicle.name,
      vehicleId: nextSandboxVehicleId(),
      swCapacity: vehicle.wheelchairCapacity,
      soCapacity: vehicle.seatingCapacity,
      cooldownMinutes: vehicle.cooldownMinutes,
      source: "existing",
      originalId: vehicle.id,
    };
    setSandboxVehicles([...sandboxVehicles, sandboxVehicle]);
  };

  // Add custom vehicle
  const addCustomVehicle = (type: "minibus" | "bus" | "van") => {
    const template = VEHICLE_TEMPLATES[type];
    const sandboxVehicle: SandboxVehicle = {
      id: nextSandboxVehicleId(),
      name: tc('sidebar.settings'),

      vehicleId: nextSandboxVehicleId(),
      swCapacity: template.swCapacity,
      soCapacity: template.soCapacity,
      cooldownMinutes: template.cooldownMinutes,
      source: "custom",
    };
    setSandboxVehicles([...sandboxVehicles, sandboxVehicle]);
  };

  // Update vehicle in sandbox
  const updateSandboxVehicle = (id: string, updates: Partial<SandboxVehicle>) => {
    setSandboxVehicles(
      sandboxVehicles.map((v) => (v.id === id ? { ...v, ...updates } : v))
    );
  };

  // Remove vehicle from sandbox
  const removeSandboxVehicle = (id: string) => {
    setSandboxVehicles(sandboxVehicles.filter((v) => v.id !== id));
  };

  // Toggle student selection
  const toggleStudent = (studentId: string) => {
    setSelectedStudentIds((prev) =>
      prev.includes(studentId)
        ? prev.filter((id) => id !== studentId)
        : [...prev, studentId]
    );
  };

  // Select all students by type
  const selectAllByType = (type: "Sw" | "So" | "all") => {
    if (type === "all") {
      setSelectedStudentIds(students.map((s) => s.id));
    } else {
      const ids = students
        .filter((s) => (s.disability_type || s.disabilityType) === type)
        .map((s) => s.id);
      setSelectedStudentIds((prev) => [...new Set([...prev, ...ids])]);
    }
  };

  // Clear all students
  const clearAllStudents = () => {
    setSelectedStudentIds([]);
  };

  // Run IE analysis
  const runAnalysis = async () => {
    if (sandboxVehicles.length === 0) {
      toast({
        title: t('noVehicle'),
        description: t('noVehicle'),
        variant: "destructive",
      });
      return;
    }

    if (selectedStudentIds.length === 0) {
      toast({
        title: t('noStudent'),
        description: t('noStudent'),
        variant: "destructive",
      });
      return;
    }

    setIsCalculating(true);
    try {
      const selectedStudents = students.filter((s) => selectedStudentIds.includes(s.id));
      const vehicleConfigs = sandboxVehicles.map((v) => ({
        name: v.name,
        swCapacity: v.swCapacity,
        soCapacity: v.soCapacity,
        cooldownMinutes: v.cooldownMinutes || 10,
      }));

      // Use sandbox API for re-optimization with custom vehicles
      const response = await fetch("/api/sandbox", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          students: selectedStudents,
          vehicles: vehicleConfigs,
          maxTourTime: 120,
          allowTimeShift: timeWindowMinutes > 0,
          strategy: "genetic_algorithm",
          clusteringAlgorithm: "sweep",
        }),
      });

      if (!response.ok) {
        throw new Error(tc('error'));
      }

      const data = await response.json();
      
      if (data.data?.ieData) {
        setIeData(data.data.ieData);
        setActiveTab("results");
        toast({
          title: tc('success'),
          description: tc('success'),
        });
      } else if (data.ieData) {
        setIeData(data.ieData);
        setActiveTab("results");
        toast({
          title: tc('success'),
          description: tc('success'),
        });
      } else {
        toast({
          title: tc('error'),
          description: tc('error'),
          variant: "destructive",
        });
      }
    } catch (error: any) {
        toast({
          title: tc('error'),
          description: error.message,
          variant: "destructive",
        });
    } finally {
      setIsCalculating(false);
    }
  };

  // Save current scenario
  const saveScenario = () => {
    if (!scenarioName.trim()) {
      toast({
        title: tc('error'),
        description: t('noVehicle'),
        variant: "destructive",
      });
      return;
    }

    const newScenario: SandboxScenario = {
      id: `sc-${Date.now()}`,
      name: scenarioName.trim(),
      vehicles: [...sandboxVehicles],
      studentIds: [...selectedStudentIds],
      timeWindowMinutes,
      createdAt: new Date().toISOString(),
    };

    const updated = [...savedScenarios, newScenario];
    saveScenarios(updated);
    setScenarioName("");
    
    toast({
      title: tc('success'),
      description: `"${newScenario.name}" ${tc('success')}`,
    });
  };

  // Load scenario
  const loadScenario = (scenario: SandboxScenario) => {
    setSandboxVehicles(scenario.vehicles);
    setSelectedStudentIds(scenario.studentIds);
    setTimeWindowMinutes(scenario.timeWindowMinutes);
    
    toast({
      title: tc('success'),
      description: `"${scenario.name}" ${tc('success')}`,
    });
  };

  // Delete scenario
  const deleteScenario = (scenarioId: string) => {
    const updated = savedScenarios.filter((s) => s.id !== scenarioId);
    saveScenarios(updated);
    
    toast({
      title: tc('success'),
      description: tc('success'),
    });
  };

  // Reset sandbox
  const resetSandbox = () => {
    setSandboxVehicles([]);
    setSelectedStudentIds([]);
    setIeData(null);
    setActiveTab("configure");
  };

  // Filter students by type
  const swStudents = students.filter(
    (s) => (s.disability_type || s.disabilityType) === "Sw"
  );
  const soStudents = students.filter(
    (s) =>
      (s.disability_type || s.disabilityType) === "So" ||
      !(s.disability_type || s.disabilityType)
  );

  const selectedSwCount = swStudents.filter((s) =>
    selectedStudentIds.includes(s.id)
  ).length;
  const selectedSoCount = soStudents.filter((s) =>
    selectedStudentIds.includes(s.id)
  ).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <FlaskConical className="h-6 w-6 text-primary" />
            IE Sandbox
          </h1>
          <p className="text-muted-foreground">
            {tc('sidebar.settings')}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={resetSandbox}>
            {tc('clear')}
          </Button>
          <Button onClick={runAnalysis} disabled={isCalculating}>
            <Play className="h-4 w-4 mr-2" />
            {isCalculating ? tc('loading') : tc('selectAll')}
          </Button>
        </div>
      </div>

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3 lg:w-auto">
          <TabsTrigger value="configure" className="flex items-center gap-2">
            <Settings2 className="h-4 w-4" />
            <span>{tc('configuration')}</span>
          </TabsTrigger>
          <TabsTrigger value="scenarios" className="flex items-center gap-2">
            <Save className="h-4 w-4" />
            <span>{tc('save')}</span>
          </TabsTrigger>
          <TabsTrigger value="results" className="flex items-center gap-2" disabled={!ieData}>
            <BarChart3 className="h-4 w-4" />
            <span>{tc('details')}</span>
          </TabsTrigger>
        </TabsList>

        {/* Configure Tab */}
        <TabsContent value="configure" className="space-y-6 mt-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Vehicle Configuration */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Truck className="h-5 w-5" />
                    {tc('select')}
                  </CardTitle>
                  <CardDescription>
                    {tc('selectAll')}
                  </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Existing Vehicles */}
                <div className="space-y-2">
                  <Label>{tc('sidebar.settings')}</Label>
                  <div className="flex flex-wrap gap-2">
                    {existingVehicles
                      .filter((v) => v.status === "active")
                      .map((vehicle) => (
                        <Button
                          key={vehicle.id}
                          variant="outline"
                          size="sm"
                          onClick={() => addExistingVehicle(vehicle)}
                          disabled={sandboxVehicles.some(
                            (sv) => sv.originalId === vehicle.id
                          )}
                        >
                          <Plus className="h-3 w-3 mr-1" />
                          {vehicle.name}
                        </Button>
                      ))}
                    {existingVehicles.filter((v) => v.status === "active").length === 0 && (
                      <p className="text-sm text-muted-foreground">
                        {tc('noResults')}
                      </p>
                    )}
                  </div>
                </div>

                <Separator />

                {/* Custom Vehicles */}
                <div className="space-y-2">
                  <Label>{tc('sidebar.settings')}</Label>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => addCustomVehicle("minibus")}
                    >
                      <Plus className="h-3 w-3 mr-1" />
                      {tc('sidebar.settings')}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => addCustomVehicle("bus")}
                    >
                      <Plus className="h-3 w-3 mr-1" />
                      {tc('sidebar.settings')}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => addCustomVehicle("van")}
                    >
                      <Plus className="h-3 w-3 mr-1" />
                      {tc('sidebar.settings')}
                    </Button>
                  </div>
                </div>

                <Separator />

                {/* Sandbox Vehicles List */}
                <div className="space-y-2">
                  <Label>{tc('sidebar.vehicleManagement')} ({sandboxVehicles.length})</Label>
                  {sandboxVehicles.length === 0 ? (
                    <p className="text-sm text-muted-foreground p-4 bg-muted rounded">
                      {tc('noResults')}
                    </p>
                  ) : (
                    <ScrollArea className="h-48 rounded border">
                      <div className="p-2 space-y-2">
                        {sandboxVehicles.map((vehicle) => (
                          <div
                            key={vehicle.id}
                            className="p-3 bg-muted rounded space-y-2"
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <Input
                                  value={vehicle.name}
                                  onChange={(e) =>
                                    updateSandboxVehicle(vehicle.id, {
                                      name: e.target.value,
                                    })
                                  }
                                  className="h-7 w-32"
                                />
                                {vehicle.source === "existing" ? (
                                  <Badge variant="outline" className="text-xs">
                                    {tc('selectAll')}
                                  </Badge>
                                ) : (
                                  <Badge variant="secondary" className="text-xs">
                                    {tc('sidebar.settings')}
                                  </Badge>
                                )}
                              </div>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => removeSandboxVehicle(vehicle.id)}
                              >
                                <Trash2 className="h-4 w-4 text-red-500" />
                              </Button>
                            </div>
                            <div className="grid grid-cols-3 gap-2 text-sm">
                              <div>
                                <Label className="text-xs">Sw</Label>
                                <Input
                                  type="number"
                                  value={vehicle.swCapacity}
                                  onChange={(e) =>
                                    updateSandboxVehicle(vehicle.id, {
                                      swCapacity: parseInt(e.target.value) || 0,
                                    })
                                  }
                                  className="h-7"
                                />
                              </div>
                              <div>
                                <Label className="text-xs">So</Label>
                                <Input
                                  type="number"
                                  value={vehicle.soCapacity}
                                  onChange={(e) =>
                                    updateSandboxVehicle(vehicle.id, {
                                      soCapacity: parseInt(e.target.value) || 0,
                                    })
                                  }
                                  className="h-7"
                                />
                              </div>
                              <div>
                                <Label className="text-xs">Cooldown</Label>
                                <Input
                                  type="number"
                                  value={vehicle.cooldownMinutes}
                                  onChange={(e) =>
                                    updateSandboxVehicle(vehicle.id, {
                                      cooldownMinutes:
                                        parseInt(e.target.value) || 0,
                                    })
                                  }
                                  className="h-7"
                                />
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </ScrollArea>
                  )}
                </div>

                {/* Total Capacity Summary */}
                {sandboxVehicles.length > 0 && (
                  <div className="p-3 bg-primary/5 rounded">
                    <div className="text-sm font-medium">{t('scenarioName')}</div>
                    <div className="text-sm text-muted-foreground">
                      {sandboxVehicles.reduce(
                        (sum, v) => sum + v.swCapacity,
                        0
                      )}{" "}
                      Sw |{" "}
                      {sandboxVehicles.reduce(
                        (sum, v) => sum + v.soCapacity,
                        0
                      )}{" "}
                      So | {sandboxVehicles.length} {tc('sidebar.vehicleManagement')}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Student Selection */}
            <Card>
              <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Users className="h-5 w-5" />
                    {t('studentSelection')}
                  </CardTitle>
                  <CardDescription>
                    {t('studentSelectionDesc')}
                  </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Summary */}
                <div className="flex gap-2">
                  <Badge variant="outline">
                    {selectedStudentIds.length} {tc('select')}
                  </Badge>
                  <Badge variant="outline">{selectedSwCount} Sw</Badge>
                  <Badge variant="outline">{selectedSoCount} So</Badge>
                </div>

                {/* Quick Select Buttons */}
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => selectAllByType("Sw")}
                  >
                    Sw
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => selectAllByType("So")}
                  >
                    So
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => selectAllByType("all")}
                  >
                    {tc('all')}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={clearAllStudents}>
                    {tc('clear')}
                  </Button>
                </div>

                <Separator />

                {/* Time Window */}
                <div className="space-y-3">
                  <Label className="flex items-center gap-2">
                    <Clock className="h-4 w-4" />
                    {tc('details')}: {timeWindowMinutes} {tc('filter')}
                  </Label>
                  <Slider
                    value={[timeWindowMinutes]}
                    onValueChange={(value) => setTimeWindowMinutes(value[0])}
                    min={0}
                    max={60}
                    step={10}
                  />
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>0 dk</span>
                    <span>10 dk</span>
                    <span>20 dk</span>
                    <span>30 dk</span>
                    <span>40 dk</span>
                    <span>50 dk</span>
                    <span>60 dk</span>
                  </div>
                </div>

                <Separator />

                {/* Student List */}
                <ScrollArea className="h-64 rounded border p-2">
                  {isLoading ? (
                    <p className="text-muted-foreground text-center py-4">
                      {tc('loading')}
                    </p>
                  ) : students.length === 0 ? (
                    <p className="text-muted-foreground text-center py-4">
                      {tc('noResults')}
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {/* Sw Students */}
                      {swStudents.length > 0 && (
                        <div>
                          <p className="text-xs font-semibold text-muted-foreground mb-2">
                            Sw ({swStudents.length})
                          </p>
                          <div className="grid grid-cols-2 gap-1">
                            {swStudents.map((student) => (
                              <div
                                key={student.id}
                                className="flex items-center space-x-2"
                              >
                                <Checkbox
                                  id={`sw-${student.id}`}
                                  checked={selectedStudentIds.includes(
                                    student.id
                                  )}
                                  onCheckedChange={() =>
                                    toggleStudent(student.id)
                                  }
                                />
                                <Label
                                  htmlFor={`sw-${student.id}`}
                                  className="text-xs cursor-pointer"
                                >
                                  {student.location_code ||
                                    student.locationCode ||
                                    student.name}
                                </Label>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* So Students */}
                      {soStudents.length > 0 && (
                        <div>
                          <p className="text-xs font-semibold text-muted-foreground mb-2 mt-4">
                            So ({soStudents.length})
                          </p>
                          <div className="grid grid-cols-2 gap-1">
                            {soStudents.map((student) => (
                              <div
                                key={student.id}
                                className="flex items-center space-x-2"
                              >
                                <Checkbox
                                  id={`so-${student.id}`}
                                  checked={selectedStudentIds.includes(
                                    student.id
                                  )}
                                  onCheckedChange={() =>
                                    toggleStudent(student.id)
                                  }
                                />
                                <Label
                                  htmlFor={`so-${student.id}`}
                                  className="text-xs cursor-pointer"
                                >
                                  {student.location_code ||
                                    student.locationCode ||
                                    student.name}
                                </Label>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>
          </div>

          {/* Save Scenario */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-4">
                <Input
                  placeholder={t('scenarioPlaceholder')}
                  value={scenarioName}
                  onChange={(e) => setScenarioName(e.target.value)}
                  className="flex-1"
                />
                <Button
                  onClick={saveScenario}
                  disabled={
                    !scenarioName.trim() ||
                    sandboxVehicles.length === 0 ||
                    selectedStudentIds.length === 0
                  }
                >
                  <Save className="h-4 w-4 mr-2" />
                  {tc('save')}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Scenarios Tab */}
        <TabsContent value="scenarios" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>{tc('save')}</CardTitle>
              <CardDescription>
                {tc('sidebar.settings')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {savedScenarios.length === 0 ? (
                <div className="text-center py-8">
                  <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">
                    {tc('noResults')}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {tc('configuration')}
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {savedScenarios.map((scenario) => (
                    <div
                      key={scenario.id}
                      className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <div>
                        <h4 className="font-medium">{scenario.name}</h4>
                        <p className="text-sm text-muted-foreground">
                          {scenario.vehicles.length} | {scenario.studentIds.length} {tc('select')} | {scenario.timeWindowMinutes} dk
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {new Date(scenario.createdAt).toLocaleString("tr-TR")}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => loadScenario(scenario)}
                        >
                          {tc('loading')}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => deleteScenario(scenario.id)}
                        >
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Results Tab */}
        <TabsContent value="results" className="mt-6">
          {ieData ? (
            <IEDashboard
              ieData={ieData}
              availableVehicles={sandboxVehicles.map((v) => ({
                vehicleId: v.vehicleId,
                name: v.name,
                swCapacity: v.swCapacity,
                soCapacity: v.soCapacity,
                cooldownMinutes: v.cooldownMinutes,
              }))}
              onRefresh={runAnalysis}
              onExport={() => {
                const dataStr = JSON.stringify(ieData, null, 2);
                const blob = new Blob([dataStr], { type: "application/json" });
                const url = URL.createObjectURL(blob);
                const link = document.createElement("a");
                link.href = url;
                link.download = `ie-analysis-${Date.now()}.json`;
                link.click();
                  toast({
                    title: tc('success'),
                    description: tc('success'),
                  });
              }}
            />
          ) : (
            <div className="text-center py-12">
              <Calculator className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">
                    {tc('noResults')}
              </p>
              <Button
                className="mt-4"
                onClick={() => setActiveTab("configure")}
              >
                {tc('configuration')}
              </Button>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
