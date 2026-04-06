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
import { resetPasswordForEmail } from "@/lib/supabase-auth";
import { useState } from "react";
import { Mail, ArrowLeft, Bug } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import Link from "next/link";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
    CardFooter,
} from "@/components/ui/card";

const forgotPasswordSchema = z.object({
    email: z.string().email({ message: "Geçerli bir e-posta adresi giriniz." }),
});

type ForgotPasswordValues = z.infer<typeof forgotPasswordSchema>;

export default function ForgotPasswordPage() {
    const { toast } = useToast();
    const [isLoading, setIsLoading] = useState(false);
    const [isSent, setIsSent] = useState(false);

    const form = useForm<ForgotPasswordValues>({
        resolver: zodResolver(forgotPasswordSchema),
        defaultValues: {
            email: "",
        },
    });

    async function onSubmit(data: ForgotPasswordValues) {
        setIsLoading(true);
        try {
            await resetPasswordForEmail(data.email);
            setIsSent(true);
            toast({
                title: "E-posta Gönderildi",
                description: "Şifre sıfırlama bağlantısı e-posta adresinize gönderildi. Lütfen gelen kutunuzu kontrol edin.",
            });
        } catch (error: any) {
            toast({
                title: "Hata",
                description: error.message || "Şifre sıfırlama e-postası gönderilirken bir hata oluştu.",
                variant: "destructive",
            });
        } finally {
            setIsLoading(false);
        }
    }

    async function handleDevReset() {
        const email = form.getValues().email;
        if (!email) {
            toast({ title: "Email gerekli", description: "Lütfen bir email girin.", variant: "destructive" });
            return;
        }

        const newPass = prompt("Test hesabı için kullanılacak yeni şifreyi girin (En az 6 karakter):");
        if (!newPass || newPass.length < 6) return;

        setIsLoading(true);
        try {
            const res = await fetch("/api/auth/dev-reset", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, newPassword: newPass })
            });
            const data = await res.json();

            if (res.ok) {
                toast({ title: "Dev Reset Başarılı", description: "Test şifresi anında değiştirildi. Giriş yapabilirsiniz." });
            } else {
                toast({ title: "Dev Reset Hatası", description: data.error || "Yetki eksik veya hata oluştu.", variant: "destructive" });
            }
        } catch (e) {
            toast({ title: "Bağlantı Hatası", description: "Sunucuya ulaşılamadı.", variant: "destructive" });
        } finally {
            setIsLoading(false);
        }
    }

    return (
        <main className="flex min-h-screen flex-col items-center justify-center p-6 bg-background">
            <Card className="w-full max-w-md shadow-xl">
                <CardHeader className="text-center">
                    <CardTitle className="text-2xl font-bold text-primary">Şifremi Unuttum</CardTitle>
                    <CardDescription>
                        Sisteme kayıtlı e-posta adresinizi girin. Size şifrenizi sıfırlayabilmeniz için bir bağlantı göndereceğiz.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {!isSent ? (
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

                                <Button type="submit" className="w-full" disabled={isLoading}>
                                    {isLoading ? "Gönderiliyor..." : "Sıfırlama Bağlantısı Gönder"}
                                    {!isLoading && <Mail className="ml-2 h-4 w-4" />}
                                </Button>
                            </form>
                        </Form>
                    ) : (
                        <div className="text-center p-4 bg-green-50 text-green-800 rounded-lg dark:bg-green-900/20 dark:text-green-400">
                            <Mail className="mx-auto h-8 w-8 mb-2" />
                            <h3 className="font-semibold text-lg mb-1">E-posta Gönderildi!</h3>
                            <p className="text-sm">
                                Lütfen e-posta kutunuzu (ve gerekiyorsa Spam klasörünü) kontrol edin ve gelen bağlantıya tıklayarak şifrenizi sıfırlayın.
                            </p>
                        </div>
                    )}
                </CardContent>
                <CardFooter className="flex flex-col gap-4 border-t p-4">
                    <Link href="/login" className="flex items-center text-sm font-medium text-muted-foreground hover:text-primary transition-colors">
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        Giriş sayfasına geri dön
                    </Link>

                    {process.env.NODE_ENV === "development" && (
                        <Button variant="outline" size="sm" type="button" onClick={handleDevReset} className="w-full text-xs text-orange-500 border-orange-200 hover:bg-orange-50">
                            <Bug className="h-3 w-3 mr-2" />
                            [Geliştirici] Doğrudan Şifre Atama (Test Hesapları İçin)
                        </Button>
                    )}
                </CardFooter>
            </Card>
        </main>
    );
}
