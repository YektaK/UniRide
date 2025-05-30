
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
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { useAuth } from "@/hooks/use-auth";
import { useRouter } from "next/navigation";
import type { UserRole } from "@/types";
import { LogIn, KeyRound } from "lucide-react"; // Added KeyRound
import { useToast } from "@/hooks/use-toast";

const loginFormSchema = z.object({
  emailOrUsername: z.string().min(1, { message: "Lütfen e-posta veya kullanıcı adınızı girin." }),
  password: z.string().min(1, { message: "Lütfen şifrenizi girin." }),
  role: z.enum(["student", "admin"], {
    required_error: "Lütfen bir rol seçin.",
  }),
});

type LoginFormValues = z.infer<typeof loginFormSchema>;

export default function LoginForm() {
  const { login, isLoading, user } = useAuth(); // Added user to check auth state
  const router = useRouter();
  const { toast } = useToast();

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginFormSchema),
    defaultValues: {
      emailOrUsername: "",
      password: "",
      role: "student",
    },
  });

  async function onSubmit(data: LoginFormValues) {
    login(data.emailOrUsername, data.password, data.role as UserRole);
    
    // AuthContext will handle navigation on successful login via useEffect in HomePage or (app) layout
    // For demo purposes, we'll check after a delay if login attempt leads to user state change.
    setTimeout(() => {
      // Check localStorage directly as user state update might have a slight delay
      const storedUser = localStorage.getItem("uniRideUser");
      if (storedUser) { 
        toast({
          title: "Giriş Başarılı",
          description: "Kontrol paneline yönlendiriliyorsunuz...",
        });
        router.push("/dashboard");
      } else {
         toast({
          title: "Giriş Başarısız",
          description: "E-posta/kullanıcı adı, şifre veya rol hatalı. Lütfen bilgilerinizi kontrol edin. Örnek: student@uniride.com / studentpassword (Öğrenci) veya admin@uniride.com / adminpassword (Admin).",
          variant: "destructive",
        });
      }
    }, 700); 
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
        <FormField
          control={form.control}
          name="role"
          render={({ field }) => (
            <FormItem className="space-y-3">
              <FormLabel>Rolünüz</FormLabel>
              <FormControl>
                <RadioGroup
                  onValueChange={field.onChange}
                  defaultValue={field.value}
                  className="flex flex-col space-y-1"
                >
                  <FormItem className="flex items-center space-x-3 space-y-0">
                    <FormControl>
                      <RadioGroupItem value="student" />
                    </FormControl>
                    <FormLabel className="font-normal">Öğrenci</FormLabel>
                  </FormItem>
                  <FormItem className="flex items-center space-x-3 space-y-0">
                    <FormControl>
                      <RadioGroupItem value="admin" />
                    </FormControl>
                    <FormLabel className="font-normal">Admin</FormLabel>
                  </FormItem>
                </RadioGroup>
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? "Giriş Yapılıyor..." : "Giriş Yap"}
          {!isLoading && <LogIn className="ml-2 h-4 w-4" />}
        </Button>
      </form>
    </Form>
  );
}
