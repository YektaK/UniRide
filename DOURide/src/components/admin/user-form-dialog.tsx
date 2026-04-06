
"use client";

import type { User, UserRole } from "@/types";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import React, { useEffect } from "react";

interface UserFormDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (user: User) => void;
  user: User | null;
}

const disabilityTypeOptions = [
  { id: "Sw", label: "Sw - Tekerlekli Sandalye" },
  { id: "So", label: "So - Diğer Engel Tipi" },
];

const accessibilityNeedsOptions = [
  { id: "visual_impairment", label: "Görme Engelli" },
  { id: "hearing_impairment", label: "İşitme Engelli" },
  { id: "mobility_aid", label: "Yürüme Desteği" },
  { id: "other", label: "Diğer" },
];

// Role is no longer part of the editable form values
const userFormSchema = z.object({
  id: z.string(),
  name: z.string().min(2, { message: "Ad Soyad en az 2 karakter olmalıdır." }),
  email: z.string().email({ message: "Geçerli bir e-posta adresi girin." }),
  studentNumber: z.string().optional(),
  homeAddress: z.string().optional(),
  disabilityType: z.enum(["Sw", "So"]).nullable().optional(),
  accessibilityNeeds: z.array(z.string()).optional(),
  otherAccessibilityNeed: z.string().optional(),
  locationCode: z.string().optional(),
  password: z.string().optional(),
  weeklyScheduleId: z.string().optional(),
  role: z.enum(["student", "admin", "driver"]) as z.ZodType<UserRole>, // Extended roles
}).refine(data => {
  // Student number validation only if the user's role is "student"
  if (data.role === "student" && (!data.studentNumber || !/^\d{12}$/.test(data.studentNumber))) {
    return false;
  }
  return true;
}, {
  message: "Öğrenci rolü için 12 haneli öğrenci numarası gereklidir.",
  path: ["studentNumber"],
});

type UserFormValues = z.infer<typeof userFormSchema>;

export default function UserFormDialog({ isOpen, onClose, onSave, user }: UserFormDialogProps) {
  const form = useForm<UserFormValues>({
    resolver: zodResolver(userFormSchema),
  });

  useEffect(() => {
    if (isOpen && user) {
      form.reset({
        ...user,
        studentNumber: user.studentNumber || "",
        homeAddress: user.homeAddress || "",
        disabilityType: user.disabilityType || null,
        locationCode: (user as any).locationCode || "",
        accessibilityNeeds: user.accessibilityNeeds || [],
        otherAccessibilityNeed: user.accessibilityNeeds?.includes("other")
          ? user.accessibilityNeeds.find(n => n.startsWith("other:"))?.split(":")[1] || ""
          : "",
      });
    } else if (isOpen && !user) {
      form.reset({
        id: `new-${Date.now()}`,
        name: "",
        email: "",
        role: "student",
        studentNumber: "",
        homeAddress: "",
        disabilityType: null,
        accessibilityNeeds: [],
        otherAccessibilityNeed: ""
      });
    }
  }, [user, form, isOpen]);

  const handleSubmit = (data: UserFormValues) => {
    const finalAccessibilityNeeds = data.accessibilityNeeds?.filter(need => need !== "other") || [];
    if (data.accessibilityNeeds?.includes("other") && data.otherAccessibilityNeed) {
      finalAccessibilityNeeds.push(`other:${data.otherAccessibilityNeed}`);
    }

    const userDataToSave: User = {
      ...(user!),
      ...data,
      role: user!.role,
      accessibilityNeeds: finalAccessibilityNeeds,
    };

    // Correctly apply Sw/So/Null logic based on role
    if (userDataToSave.role === 'admin' || userDataToSave.role === 'driver') {
      userDataToSave.studentNumber = undefined;
      userDataToSave.homeAddress = undefined;
      userDataToSave.accessibilityNeeds = [];
      userDataToSave.disabilityType = null;
    } else {
      // For students, use what was in the form, ensuring it's Sw, So, or null
      userDataToSave.disabilityType = data.disabilityType || null;
    }

    onSave(userDataToSave);
  };

  if (!user && isOpen) return <Dialog open={isOpen} onOpenChange={onClose}><DialogContent><p>Kullanıcı yüklenemedi.</p></DialogContent></Dialog>;


  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Kullanıcıyı Düzenle: {user?.name} ({user?.role === "admin" ? "Admin" : user?.role === "driver" ? "Şoför" : "Öğrenci"})</DialogTitle>
          <DialogDescription>
            Kullanıcı bilgilerini güncelleyin. E-posta değişikliği dikkatli yapılmalıdır. Rol bu ekrandan değiştirilemez.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4 py-4 max-h-[70vh] overflow-y-auto pr-2">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Ad Soyad</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>E-posta</FormLabel>
                  <FormControl>
                    <Input type="email" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Role selection field is removed */}

            {user?.role === "student" && ( // Conditionally render based on the original user's role
              <>
                <FormField
                  control={form.control}
                  name="studentNumber"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Öğrenci Numarası</FormLabel>
                      <FormControl>
                        <Input placeholder="12 haneli numara" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="disabilityType"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Engel Tipi</FormLabel>
                      <div className="flex gap-4">
                        {disabilityTypeOptions.map((option) => (
                          <label key={option.id} className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="radio"
                              name="disabilityType"
                              value={option.id}
                              checked={field.value === option.id}
                              onChange={() => field.onChange(option.id)}
                              className="w-4 h-4"
                            />
                            <span className="text-sm">{option.label}</span>
                          </label>
                        ))}
                      </div>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="homeAddress"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Ev Adresi</FormLabel>
                      <FormControl>
                        <Textarea placeholder="Tam ev adresi" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="accessibilityNeeds"
                  render={() => (
                    <FormItem>
                      <div className="mb-2">
                        <FormLabel className="text-base">Erişilebilirlik İhtiyaçları</FormLabel>
                      </div>
                      {accessibilityNeedsOptions.map((item) => (
                        <FormField
                          key={item.id}
                          control={form.control}
                          name="accessibilityNeeds"
                          render={({ field: checkboxField }) => {
                            return (
                              <FormItem
                                key={item.id}
                                className="flex flex-row items-start space-x-3 space-y-0 mb-2"
                              >
                                <FormControl>
                                  <Checkbox
                                    checked={checkboxField.value?.includes(item.id)}
                                    onCheckedChange={(checked) => {
                                      return checked
                                        ? checkboxField.onChange([...(checkboxField.value || []), item.id])
                                        : checkboxField.onChange(
                                          checkboxField.value?.filter(
                                            (value) => value !== item.id
                                          )
                                        );
                                    }}
                                  />
                                </FormControl>
                                <FormLabel className="font-normal">
                                  {item.label}
                                </FormLabel>
                              </FormItem>
                            );
                          }}
                        />
                      ))}
                      <FormMessage />
                    </FormItem>
                  )}
                />
                {form.watch("accessibilityNeeds")?.includes("other") && (
                  <FormField
                    control={form.control}
                    name="otherAccessibilityNeed"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Diğer Erişilebilirlik İhtiyacı</FormLabel>
                        <FormControl>
                          <Input placeholder="Lütfen belirtin..." {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                )}
              </>
            )}

            <DialogFooter className="pt-4">
              <Button type="button" variant="outline" onClick={onClose}>
                İptal
              </Button>
              <Button type="submit">Kaydet</Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}

