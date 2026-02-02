
"use client";

import type { User } from "@/types";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
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
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { useToast } from "@/hooks/use-toast";
import { Save, MapPin, Hash } from "lucide-react";
import { updateUser as dbUpdateUser } from "@/lib/database";

interface ProfileFormProps {
  currentUser: User;
  onUpdateProfile: (updatedUser: User) => void; // This is effectively setUser from AuthContext
}

const accessibilityNeedsOptions = [
  { id: "wheelchair", label: "Tekerlekli Sandalye Kullanıcısı" },
  { id: "visual_impairment", label: "Görme Engelli" },
  { id: "hearing_impairment", label: "İşitme Engelli" },
  { id: "other", label: "Diğer (Lütfen belirtin)" },
];

const profileFormSchema = z.object({
  name: z.string().min(2, { message: "İsim en az 2 karakter olmalıdır." }),
  email: z.string().email({ message: "Geçerli bir e-posta adresi girin." }),
  studentNumber: z.string().optional(),
  homeAddress: z.string().min(10, { message: "Ev adresi en az 10 karakter olmalıdır." }).optional(),
  accessibilityNeeds: z.array(z.string()).optional(),
  otherAccessibilityNeed: z.string().optional(),
  // Password fields can be added here if password change is desired on this form
});

type ProfileFormValues = z.infer<typeof profileFormSchema>;

export default function ProfileForm({ currentUser, onUpdateProfile }: ProfileFormProps) {
  const { toast } = useToast();
  const form = useForm<ProfileFormValues>({
    resolver: zodResolver(profileFormSchema),
    defaultValues: {
      name: currentUser.name || "",
      email: currentUser.email || "",
      studentNumber: currentUser.studentNumber || "",
      homeAddress: currentUser.homeAddress || "",
      accessibilityNeeds: currentUser.accessibilityNeeds || [],
      otherAccessibilityNeed: currentUser.accessibilityNeeds?.includes("other") ? currentUser.accessibilityNeeds.find(n => n.startsWith("other:"))?.split(":")[1] || "" : "",
    },
  });

  async function onSubmit(data: ProfileFormValues) {
    const finalAccessibilityNeeds = data.accessibilityNeeds?.filter(need => need !== "other") || [];
    if (data.accessibilityNeeds?.includes("other") && data.otherAccessibilityNeed) {
        finalAccessibilityNeeds.push(`other:${data.otherAccessibilityNeed}`);
    }

    try {
      // Update user in Firebase
      const updates: Partial<User> = {
        name: data.name,
      };

      if (currentUser.role === 'student') {
        updates.studentNumber = data.studentNumber;
        updates.homeAddress = data.homeAddress;
        updates.accessibilityNeeds = finalAccessibilityNeeds;
      }

      await dbUpdateUser(currentUser.id, updates);

      // Update in AuthContext
      const updatedUser: User = {
        ...currentUser,
        ...updates,
      };
      onUpdateProfile(updatedUser); 
      toast({
        title: "Profil Güncellendi",
        description: "Bilgileriniz başarıyla kaydedildi.",
      });
    } catch (error) {
      console.error("Error updating profile:", error);
      toast({
        title: "Güncelleme Başarısız",
        description: "Profiliniz güncellenirken bir hata oluştu.",
        variant: "destructive",
      });
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Ad Soyad</FormLabel>
              <FormControl>
                <Input placeholder="Adınız Soyadınız" {...field} />
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
              <FormLabel>E-posta Adresi</FormLabel>
              <FormControl>
                <Input type="email" placeholder="ornek@uniride.com" {...field} readOnly disabled />
              </FormControl>
              <FormDescription>E-posta adresiniz değiştirilemez.</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        {currentUser.role === 'student' && (
          <>
            <FormField
              control={form.control}
              name="studentNumber"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Öğrenci Numarası</FormLabel>
                  <FormControl>
                    <Input placeholder="Örn: 202003002016" {...field} />
                  </FormControl>
                   <FormDescription className="flex items-center gap-1">
                    <Hash className="h-4 w-4"/> Öğrenci numaranız.
                  </FormDescription>
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
                    <Textarea placeholder="Tam ev adresinizi girin..." {...field} rows={3} />
                  </FormControl>
                  <FormDescription className="flex items-center gap-1">
                    <MapPin className="h-4 w-4"/> Konumunuz servis planlaması için kullanılacaktır.
                    Haritadan seçme özelliği yakında eklenecektir.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="accessibilityNeeds"
              render={() => (
                <FormItem>
                  <div className="mb-4">
                    <FormLabel className="text-base">Erişilebilirlik İhtiyaçları</FormLabel>
                    <FormDescription>
                      Size daha iyi hizmet verebilmemiz için lütfen ilgili seçenekleri işaretleyin.
                    </FormDescription>
                  </div>
                  {accessibilityNeedsOptions.map((item) => (
                    <FormField
                      key={item.id}
                      control={form.control}
                      name="accessibilityNeeds"
                      render={({ field }) => {
                        return (
                          <FormItem
                            key={item.id}
                            className="flex flex-row items-start space-x-3 space-y-0"
                          >
                            <FormControl>
                              <Checkbox
                                checked={field.value?.includes(item.id)}
                                onCheckedChange={(checked) => {
                                  return checked
                                    ? field.onChange([...(field.value || []), item.id])
                                    : field.onChange(
                                        field.value?.filter(
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
        
        <Button type="submit" className="w-full sm:w-auto">
          <Save className="mr-2 h-4 w-4" /> Bilgileri Kaydet
        </Button>
      </form>
    </Form>
  );
}
