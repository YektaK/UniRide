
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
import { Save, MapPin } from "lucide-react";

interface ProfileFormProps {
  currentUser: User;
  onUpdateProfile: (updatedUser: User) => void;
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
  homeAddress: z.string().min(10, { message: "Ev adresi en az 10 karakter olmalıdır." }).optional(), // Admin için opsiyonel
  accessibilityNeeds: z.array(z.string()).optional(),
  otherAccessibilityNeed: z.string().optional(),
});

type ProfileFormValues = z.infer<typeof profileFormSchema>;

export default function ProfileForm({ currentUser, onUpdateProfile }: ProfileFormProps) {
  const { toast } = useToast();
  const form = useForm<ProfileFormValues>({
    resolver: zodResolver(profileFormSchema),
    defaultValues: {
      name: currentUser.name || "",
      email: currentUser.email || "",
      homeAddress: currentUser.homeAddress || "",
      accessibilityNeeds: currentUser.accessibilityNeeds || [],
      otherAccessibilityNeed: currentUser.accessibilityNeeds?.includes("other") ? currentUser.accessibilityNeeds.find(n => n.startsWith("other:"))?.split(":")[1] || "" : "",
    },
  });

  function onSubmit(data: ProfileFormValues) {
    const finalAccessibilityNeeds = data.accessibilityNeeds?.filter(need => need !== "other") || [];
    if (data.accessibilityNeeds?.includes("other") && data.otherAccessibilityNeed) {
        finalAccessibilityNeeds.push(`other:${data.otherAccessibilityNeed}`);
    }

    const updatedUser: User = {
      ...currentUser, // Preserve existing fields like ID, role etc.
      name: data.name,
      email: data.email, // Usually email is not editable or requires verification
    };

    if (currentUser.role === 'student') {
      updatedUser.homeAddress = data.homeAddress;
      updatedUser.accessibilityNeeds = finalAccessibilityNeeds;
    } else {
      // For admin, ensure these fields are not part of the update from the form
      // or explicitly set them to undefined if they should not exist for admin.
      // Since they are optional in User type, they might already be undefined.
      // If an admin had a homeAddress for some reason, and the field is now hidden,
      // data.homeAddress would be undefined, so it would clear it if directly assigned.
      // To be safe, we only assign them if the user is a student.
      // Or, if they shouldn't exist on admin AT ALL, delete them:
      // delete updatedUser.homeAddress;
      // delete updatedUser.accessibilityNeeds;
      // For now, we assume they might exist but are not editable for admin via this form.
    }


    onUpdateProfile(updatedUser);
    localStorage.setItem("uniRideUser", JSON.stringify(updatedUser)); // Update mock storage

    toast({
      title: "Profil Güncellendi",
      description: "Bilgileriniz başarıyla kaydedildi.",
    });
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
        
        {/* Google Maps API Key field removed */}

        <Button type="submit" className="w-full sm:w-auto">
          <Save className="mr-2 h-4 w-4" /> Bilgileri Kaydet
        </Button>
      </form>
    </Form>
  );
}
