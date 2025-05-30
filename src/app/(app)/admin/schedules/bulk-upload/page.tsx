
"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Upload, ArrowLeft, FileText } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useRouter } from "next/navigation";

export default function BulkScheduleUploadPage() {
  const { toast } = useToast();
  const router = useRouter();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setSelectedFile(event.target.files[0]);
    } else {
      setSelectedFile(null);
    }
  };

  const handleBulkUpload = () => {
    if (!selectedFile) {
      toast({
        title: "Dosya Seçilmedi",
        description: "Lütfen yüklemek için bir CSV dosyası seçin.",
        variant: "destructive",
      });
      return;
    }
    // In a real app, this would handle file processing.
    // For now, just show a toast.
    toast({
      title: "Toplu Yükleme Başlatıldı (Simülasyon)",
      description: `${selectedFile.name} dosyası seçildi ve işleniyor. Bu özellik yakında tam olarak aktif olacaktır.`,
    });
    // Potentially reset file input after 'upload'
    setSelectedFile(null); 
    // And clear the input field visually if possible (though this is tricky with controlled file inputs)
    const fileInput = document.getElementById('scheduleFile') as HTMLInputElement;
    if (fileInput) {
        fileInput.value = '';
    }
  };

  return (
    <div className="space-y-6">
      <Card className="shadow-lg">
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle className="text-2xl flex items-center gap-2">
              <Upload className="text-primary" /> Toplu Ders Programı Yükleme
            </CardTitle>
            <Button variant="outline" onClick={() => router.back()}>
              <ArrowLeft className="mr-2 h-4 w-4" /> Geri
            </Button>
          </div>
          <CardDescription>
            Öğrenci ders programlarını içeren bir CSV dosyası seçerek sisteme toplu olarak yükleyebilirsiniz.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="p-6 border rounded-lg bg-muted/50">
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2"><FileText className="h-5 w-5"/>Dosya Formatı ve İçeriği</h3>
            <p className="text-sm text-muted-foreground mb-1">
              Lütfen aşağıdaki formatta bir CSV dosyası hazırlayın:
            </p>
            <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1 mb-3 pl-4">
              <li>Sütunlar: <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded-sm">Öğrenci No</code>, <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded-sm">Gün</code>, <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded-sm">Ders Kodu</code>, <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded-sm">Başlangıç Saati (SS:DD)</code>, <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded-sm">Bitiş Saati (SS:DD)</code>, <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded-sm">Konum</code></li>
              <li>Günler için değerler: <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded-sm">monday</code>, <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded-sm">tuesday</code>, <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded-sm">wednesday</code>, <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded-sm">thursday</code>, <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded-sm">friday</code>, <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded-sm">saturday</code>, <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded-sm">sunday</code></li>
              <li>Konum için değerler: <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded-sm">Dudullu</code> veya <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded-sm">Çengelköy</code></li>
            </ul>
            <p className="text-xs text-muted-foreground">
              Örnek CSV satırı: <br />
              <code className="bg-gray-200 dark:bg-gray-700 p-1 rounded-sm">202003002001,monday,MAT101,09:00,11:00,Dudullu</code>
            </p>
          </div>

          <div className="space-y-2">
            <label htmlFor="scheduleFile" className="text-sm font-medium">
              Yüklenecek CSV Dosyası:
            </label>
            <Input
              id="scheduleFile"
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              className="w-full md:w-2/3"
            />
            {selectedFile && <p className="text-xs text-muted-foreground">Seçilen dosya: {selectedFile.name}</p>}
          </div>

          <div>
            <Button onClick={handleBulkUpload} disabled={!selectedFile}>
              <Upload className="mr-2 h-4 w-4" /> Yükle ve İşle
            </Button>
          </div>
          
          <CardDescription className="text-xs pt-4">
            Not: Bu özellik şu anda simülasyon modundadır. Yüklenen dosya gerçekten işlenmeyecektir.
            Toplu silme veya güncelleme işlemleri için ek geliştirmeler gerekebilir.
          </CardDescription>
        </CardContent>
      </Card>
    </div>
  );
}
