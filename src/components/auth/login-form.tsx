
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
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
// RadioGroup importları kaldırıldı
import { useAuth } from "@/hooks/use-auth";
import { useRouter } from "next/navigation";
// UserRole importu kaldırıldı
import { LogIn } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

const loginFormSchema = z.object({
  emailOrUsername: z.string().min(1, { message: "Lütfen e-posta veya kullanıcı adınızı girin." }),
  password: z.string().min(1, { message: "Lütfen şifrenizi girin." }),
  // role alanı kaldırıldı
});

type LoginFormValues = z.infer<typeof loginFormSchema>;

export default function LoginForm() {
  const { login, isLoading } = useAuth();
  const router = useRouter();
  const { toast } = useToast();

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginFormSchema),
    defaultValues: {
      emailOrUsername: "",
      password: "",
      // role default değeri kaldırıldı
    },
  });

  async function onSubmit(data: LoginFormValues) {
    try {
      await login(data.emailOrUsername, data.password);
      toast({
        title: "Giriş Başarılı",
        description: "Kontrol paneline yönlendiriliyorsunuz...",
      });
      router.push("/dashboard");
    } catch (error: any) {
      toast({
        title: "Giriş Başarısız",
        description: error.message || "E-posta/kullanıcı adı veya şifre hatalı. Lütfen bilgilerinizi kontrol edin.",
        variant: "destructive",
      });
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <FormField
          control={form.control}
          name="emailOrUsername"
          render={({ field }) => (
            <FormItem>
              <FormLabel>E-posta veya Kullanıcı Adı</FormLabel>
              <FormControl>
                <Input placeholder="ornek@uniride.com veya kullanici_adim" {...field} />
              </FormControl>
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
        {/* Rol seçimi FormField'ı kaldırıldı */}
        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? "Giriş Yapılıyor..." : "Giriş Yap"}
          {!isLoading && <LogIn className="ml-2 h-4 w-4" />}
        </Button>
      </form>
    </Form>
  );
}
