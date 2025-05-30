
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { UserPlus } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useRouter } from "next/navigation";

const registerFormSchema = z.object({
  name: z.string().min(2, { message: "Ad Soyad en az 2 karakter olmalıdır." }),
  email: z.string().email({ message: "Geçerli bir e-posta adresi girin." })
    .refine(email => email.endsWith(".edu.tr") || email.endsWith(".edu"), {
      message: "Lütfen geçerli bir okul e-posta adresi girin (örn: kullanici@okul.edu.tr)."
    }),
  password: z.string().min(6, { message: "Şifre en az 6 karakter olmalıdır." }),
  confirmPassword: z.string().min(6, { message: "Şifre tekrarı en az 6 karakter olmalıdır." }),
}).refine(data => data.password === data.confirmPassword, {
  message: "Şifreler eşleşmiyor.",
  path: ["confirmPassword"], // Hata mesajını bu alana ata
});

type RegisterFormValues = z.infer<typeof registerFormSchema>;

export default function RegisterForm() {
  const { toast } = useToast();
  const router = useRouter();
  // Simüle edilmiş yükleme durumu için
  const [isLoading, setIsLoading] = React.useState(false);


  const form = useForm<RegisterFormValues>({
    resolver: zodResolver(registerFormSchema),
    defaultValues: {
      name: "",
      email: "",
      password: "",
      confirmPassword: "",
    },
  });

  async function onSubmit(data: RegisterFormValues) {
    setIsLoading(true);
    console.log("Kayıt bilgileri (simülasyon):", data);
    // Burada normalde bir API çağrısı yapılır.
    // Şimdilik sadece bir gecikme ve toast mesajı ekliyoruz.
    setTimeout(() => {
      toast({
        title: "Kayıt Başarılı (Simülasyon)",
        description: "Hesabınız başarıyla oluşturuldu. Giriş sayfasına yönlendiriliyorsunuz.",
      });
      setIsLoading(false);
      router.push("/login"); // Kullanıcıyı giriş sayfasına yönlendir
    }, 1500);
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
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
              <FormLabel>Okul E-posta Adresi</FormLabel>
              <FormControl>
                <Input type="email" placeholder="ornek@okul.edu.tr" {...field} />
              </FormControl>
              <FormDescription>
                Lütfen geçerli okul e-posta adresinizi girin.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Şifre</FormLabel>
              <FormControl>
                <Input type="password" placeholder="••••••••" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="confirmPassword"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Şifre Tekrarı</FormLabel>
              <FormControl>
                <Input type="password" placeholder="••••••••" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? "Kayıt Olunuyor..." : "Kayıt Ol"}
          {!isLoading && <UserPlus className="ml-2 h-4 w-4" />}
        </Button>
      </form>
    </Form>
  );
}
