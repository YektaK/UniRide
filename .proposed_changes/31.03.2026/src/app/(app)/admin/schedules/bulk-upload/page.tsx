
"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Upload, ArrowLeft, FileText, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useRouter } from "next/navigation";
import { parseExcelFile, importSchedules } from "@/services/excel/import";

export default function BulkScheduleUploadPage() {
  const { toast } = useToast();
  const router = useRouter();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      const file = event.target.files[0];
      // Check file type
      const validExtensions = ['.csv', '.xlsx', '.xls'];
      const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
      
      if (!validExtensions.includes(fileExtension)) {
        toast({
          title: "Geçersiz Dosya Türü",
          description: "Lütfen CSV veya Excel (.xlsx, .xls) dosyası seçin.",
          variant: "destructive",
        });
        setSelectedFile(null);
        if (event.target) {
          event.target.value = '';
        }
        return;
      }
      
      setSelectedFile(file);
    } else {
      setSelectedFile(null);
    }
  };

  const handleBulkUpload = async () => {
    if (!selectedFile) {
      toast({
        title: "Dosya Seçilmedi",
        description: "Lütfen yüklemek için bir CSV veya Excel dosyası seçin.",
        variant: "destructive",
      });
      return;
    }

    setIsProcessing(true);
    try {
      // Parse Excel/CSV file
      const rows = await parseExcelFile(selectedFile);
      
      if (rows.length === 0) {
        toast({
          title: "Dosya Boş veya Geçersiz",
          description: "Dosyada geçerli veri bulunamadı. Lütfen dosya formatını kontrol edin.",
          variant: "destructive",
        });
        setIsProcessing(false);
        return;
      }

      // Import schedules
      const result = await importSchedules(rows);

      if (result.success) {
        toast({
          title: "Yükleme Başarılı",
          description: `${result.processed} satır işlendi. ${result.created} yeni program oluşturuldu, ${result.updated} program güncellendi.`,
        });
        
        // Reset form
        setSelectedFile(null);
        const fileInput = document.getElementById('scheduleFile') as HTMLInputElement;
        if (fileInput) {
          fileInput.value = '';
        }
        
        // Optionally redirect after successful upload
        // router.push('/admin/schedules');
      } else {
        const errorMessages = result.errors
          .slice(0, 5)
          .map((e) => `Satır ${e.row}: ${e.message}`)
          .join('; ');
        
        toast({
          title: "Yükleme Tamamlandı (Hatalar Var)",
          description: `${result.processed} satır işlendi. ${result.created} program oluşturuldu, ${result.updated} program güncellendi. Hatalar: ${errorMessages}${result.errors.length > 5 ? '...' : ''}`,
          variant: result.errors.length > 5 ? "destructive" : "default",
        });
      }
    } catch (error: any) {
      console.error("Error importing schedules:", error);
      toast({
        title: "Yükleme Hatası",
        description: error.message || "Dosya işlenirken bir hata oluştu. Lütfen dosya formatını kontrol edin.",
        variant: "destructive",
      });
    } finally {
      setIsProcessing(false);
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
            Öğrenci ders programlarını içeren bir CSV veya Excel (.xlsx, .xls) dosyası seçerek sisteme toplu olarak yükleyebilirsiniz.
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
              Yüklenecek CSV veya Excel Dosyası:
            </label>
            <Input
              id="scheduleFile"
              type="file"
              accept=".csv,.xlsx,.xls"
              onChange={handleFileChange}
              className="w-full md:w-2/3"
              disabled={isProcessing}
            />
            {selectedFile && <p className="text-xs text-muted-foreground">Seçilen dosya: {selectedFile.name}</p>}
          </div>

          <div>
            <Button onClick={handleBulkUpload} disabled={!selectedFile || isProcessing}>
              {isProcessing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> İşleniyor...
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" /> Yükle ve İşle
                </>
              )}
            </Button>
          </div>
          
          <CardDescription className="text-xs pt-4">
            Not: Yüklenen dosyalar gerçek zamanlı olarak işlenir ve öğrenci programları oluşturulur veya güncellenir.
            Mevcut programlar aynı gün için yeni verilerle değiştirilir.
          </CardDescription>
        </CardContent>
      </Card>
    </div>
  );
}
