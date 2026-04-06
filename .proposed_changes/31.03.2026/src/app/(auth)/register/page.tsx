
import RegisterForm from "@/components/auth/register-form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";

export default function RegisterPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-6 bg-background">
      <Card className="w-full max-w-md shadow-xl">
        <CardHeader className="text-center">
          <CardTitle className="text-3xl font-bold text-primary">UniRide Assist</CardTitle>
          <CardDescription>Yeni bir hesap oluşturun.</CardDescription>
        </CardHeader>
        <CardContent>
          <RegisterForm />
          <p className="mt-6 text-center text-sm text-muted-foreground">
            Zaten bir hesabınız var mı?{" "}
            <Link href="/login" className="font-semibold text-primary hover:underline">
              Giriş Yapın
            </Link>
          </p>
        </CardContent>
      </Card>
    </main>
  );
}
