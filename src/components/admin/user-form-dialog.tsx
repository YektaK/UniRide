
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

const accessibilityNeedsOptions = [
  { id: "wheelchair", label: "Tekerlekli Sandalye Kullanıcısı" },
  { id: "visual_impairment", label: "Görme Engelli" },
  { id: "hearing_impairment", label: "İşitme Engelli" },
  { id: "other", label: "Diğer (Lütfen belirtin)" },
];

// Role is no longer part of the editable form values
const userFormSchema = z.object({
  id: z.string(),
  name: z.string().min(2, { message: "Ad Soyad en az 2 karakter olmalıdır." }),
  email: z.string().email({ message: "Geçerli bir e-posta adresi girin." }),
  studentNumber: z.string().optional(),
  homeAddress: z.string().optional(),
  accessibilityNeeds: z.array(z.string()).optional(),
  otherAccessibilityNeed: z.string().optional(),
  password: z.string().optional(), 
  weeklyScheduleId: z.string().optional(), 
  role: z.enum(["student", "admin"]) as z.ZodType<UserRole>, // Keep role for data structure, but not for editing
}).refine(data => {
  // Student number validation only if the user's role (which is not editable in this form but comes with the user object) is "student"
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
        ...user, // This will include the non-editable role
        studentNumber: user.studentNumber || "",
        homeAddress: user.homeAddress || "",
        accessibilityNeeds: user.accessibilityNeeds || [],
        otherAccessibilityNeed: user.accessibilityNeeds?.includes("other")
          ? user.accessibilityNeeds.find(n => n.startsWith("other:"))?.split(":")[1] || ""
          : "",
      });
    } else if (isOpen && !user) { 
        form.reset({ // Default for a potential "add user" - though this dialog is for edit
            id: `new-${Date.now()}`, 
            name: "",
            email: "",
            role: "student", // Default role for new user if this form were used for adding
            studentNumber: "",
            homeAddress: "",
            accessibilityNeeds: [],
            otherAccessibilityNeed: ""
        });
    }
  }, [user, form, isOpen]);

  // Watched role is no longer needed for conditional rendering of form fields if role is not editable
  // const watchedRole = form.watch("role"); // No longer needed if role is not changeable here

  const handleSubmit = (data: UserFormValues) => {
    const finalAccessibilityNeeds = data.accessibilityNeeds?.filter(need => need !== "other") || [];
    if (data.accessibilityNeeds?.includes("other") && data.otherAccessibilityNeed) {
        finalAccessibilityNeeds.push(`other:${data.otherAccessibilityNeed}`);
    }

    // The user's original role is preserved from the 'user' prop
    // The 'data' object will contain the role from form.reset, but it wasn't editable.
    // We ensure the original role from the user object passed in is maintained.
    const userDataToSave: User = {
      ...(user!), // Start with existing user data to preserve password, weeklyScheduleId, and original role
      ...data, // Apply form changes (name, email, student-specific fields)
      role: user!.role, // Explicitly use the original role
      accessibilityNeeds: finalAccessibilityNeeds,
    };

    // If the user's role is admin, student-specific fields should be undefined
    if (userDataToSave.role === 'admin') {
        userDataToSave.studentNumber = undefined;
        userDataToSave.homeAddress = undefined;
        userDataToSave.accessibilityNeeds = [];
    }

    onSave(userDataToSave);
  };

  if (!user && isOpen) return <Dialog open={isOpen} onOpenChange={onClose}><DialogContent><p>Kullanıcı yüklenemedi.</p></DialogContent></Dialog>;


  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Kullanıcıyı Düzenle: {user?.name} ({user?.role === "admin" ? "Admin" : "Öğrenci"})</DialogTitle>
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

    