
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
import { LogIn } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

const loginFormSchema = z.object({
  email: z.string().email({ message: "Lütfen geçerli bir e-posta adresi girin." }),
  role: z.enum(["student", "admin"], {
    required_error: "Lütfen bir rol seçin.",
  }),
});

type LoginFormValues = z.infer<typeof loginFormSchema>;

export default function LoginForm() {
  const { login, isLoading } = useAuth();
  const router = useRouter();
  const { toast } = useToast();

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginFormSchema),
    defaultValues: {
      email: "",
      role: "student",
    },
  });

  async function onSubmit(data: LoginFormValues) {
    login(data.email, data.role as UserRole);
    // AuthContext will handle navigation on successful login via useEffect in HomePage or (app) layout
    // For demo purposes, we'll assume login might succeed or fail
    // A more robust solution would await login and then navigate or show error
    
    // Simulate redirection after a short delay to allow auth state to update
    setTimeout(() => {
      if (localStorage.getItem("uniRideUser")) { // Check if login was successful (mock)
        toast({
          title: "Giriş Başarılı",
          description: "Kontrol paneline yönlendiriliyorsunuz...",
        });
        router.push("/dashboard");
      } else {
         toast({
          title: "Giriş Başarısız",
          description: "E-posta veya rol hatalı. Lütfen 'student@uniride.com' veya 'admin@uniride.com' (admin rolüyle) deneyin.",
          variant: "destructive",
        });
      }
    }, 700); // Slightly longer than login simulation
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>E-posta Adresi</FormLabel>
              <FormControl>
                <Input placeholder="ornek@uniride.com" {...field} />
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
