
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
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import React, { useEffect } from "react";

interface UserFormDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (user: User) => void;
  user: User | null;
}

const accessibilityNeedsOptions = [
  { id: "wheelchair", label: "Tekerlekli Sandalye Kullanıcısı" },
  { id: "visual_impairment", label: "Görme Engelli" },
  { id: "hearing_impairment", label: "İşitme Engelli" },
  { id: "other", label: "Diğer (Lütfen belirtin)" },
];

const userFormSchema = z.object({
  id: z.string(),
  name: z.string().min(2, { message: "Ad Soyad en az 2 karakter olmalıdır." }),
  email: z.string().email({ message: "Geçerli bir e-posta adresi girin." }),
  role: z.enum(["student", "admin"]) as z.ZodType<UserRole>,
  studentNumber: z.string().optional(),
  homeAddress: z.string().optional(),
  accessibilityNeeds: z.array(z.string()).optional(),
  otherAccessibilityNeed: z.string().optional(),
  password: z.string().optional(), // Not directly edited, but part of User type
  weeklyScheduleId: z.string().optional(), // Not directly edited
}).refine(data => {
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
        accessibilityNeeds: user.accessibilityNeeds || [],
        otherAccessibilityNeed: user.accessibilityNeeds?.includes("other")
          ? user.accessibilityNeeds.find(n => n.startsWith("other:"))?.split(":")[1] || ""
          : "",
      });
    } else if (isOpen && !user) { // Should not happen for edit, but good for a potential "add user"
        form.reset({
            id: `new-${Date.now()}`, // Placeholder ID
            name: "",
            email: "",
            role: "student",
            studentNumber: "",
            homeAddress: "",
            accessibilityNeeds: [],
            otherAccessibilityNeed: ""
        });
    }
  }, [user, form, isOpen]);

  const watchedRole = form.watch("role");

  const handleSubmit = (data: UserFormValues) => {
    const finalAccessibilityNeeds = data.accessibilityNeeds?.filter(need => need !== "other") || [];
    if (data.accessibilityNeeds?.includes("other") && data.otherAccessibilityNeed) {
        finalAccessibilityNeeds.push(`other:${data.otherAccessibilityNeed}`);
    }

    const userDataToSave: User = {
      ...(user || {}), // Start with existing user data to preserve password, weeklyScheduleId etc.
      ...data, // Apply form changes
      accessibilityNeeds: finalAccessibilityNeeds,
    };

    if (data.role === 'admin') {
        userDataToSave.studentNumber = undefined;
        userDataToSave.homeAddress = undefined;
        userDataToSave.accessibilityNeeds = [];
        // weeklyScheduleId can be kept or cleared, let's keep it for now
    }


    onSave(userDataToSave);
  };

  if (!user && isOpen) return <Dialog open={isOpen} onOpenChange={onClose}><DialogContent><p>Kullanıcı yüklenemedi.</p></DialogContent></Dialog>;


  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Kullanıcıyı Düzenle: {user?.name}</DialogTitle>
          <DialogDescription>
            Kullanıcı bilgilerini güncelleyin. E-posta değişikliği dikkatli yapılmalıdır.
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
            <FormField
              control={form.control}
              name="role"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Rol</FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Rol seçin" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="student">Öğrenci</SelectItem>
                      <SelectItem value="admin">Admin</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            {watchedRole === "student" && (
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
