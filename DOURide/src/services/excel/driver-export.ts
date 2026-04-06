/**
 * Driver Assignment Export Service
 * Exports driver assignments to Excel and PDF formats
 */

import * as XLSX from "xlsx";
import type { RouteAssignment } from "@/types/db";
import type { Vehicle } from "@/types";
import type { DbUser } from "@/types/db";
import { format, parseISO } from "date-fns";
import { tr } from "date-fns/locale";

export interface AssignmentWithDetails {
  assignment: RouteAssignment;
  vehicle?: Vehicle;
  driver?: DbUser | null;
  students: DbUser[];
}

/**
 * Export driver assignments to Excel
 */
export const exportDriverAssignmentsToExcel = async (
  assignments: AssignmentWithDetails[],
  date: string
): Promise<void> => {
  // Prepare data for Excel
  const excelData = assignments.map((item) => {
    const { assignment, vehicle, driver, students } = item;
    return {
      "Tarih": format(parseISO(assignment.date), "dd.MM.yyyy", { locale: tr }),
      "Araç Adı": vehicle?.name || "Bilinmeyen",
      "Plaka": vehicle?.plateNumber || "-",
      "Araç Tipi": vehicle?.type || "-",
      "Kapasite": vehicle ? `${vehicle.seatingCapacity + vehicle.wheelchairCapacity}` : "-",
      "Şoför": driver?.name || "Atanmamış",
      "Şoför Email": driver?.email || "-",
      "Alış Saati": format(parseISO(assignment.pickupTime), "HH:mm", { locale: tr }),
      "Tahmini Varış": format(parseISO(assignment.estimatedDropoffTime), "HH:mm", { locale: tr }),
      "Öğrenci Sayısı": students.length,
      "Öğrenciler": students.map((s) => `${s.name}${s.studentNumber ? ` (${s.studentNumber})` : ""}`).join(", "),
      "Durum": getStatusLabel(assignment.status),
    };
  });

  // Create workbook
  const wb = XLSX.utils.book_new();
  const ws = XLSX.utils.json_to_sheet(excelData);

  // Set column widths
  const colWidths = [
    { wch: 12 }, // Tarih
    { wch: 15 }, // Araç Adı
    { wch: 12 }, // Plaka
    { wch: 12 }, // Araç Tipi
    { wch: 10 }, // Kapasite
    { wch: 20 }, // Şoför
    { wch: 25 }, // Şoför Email
    { wch: 12 }, // Alış Saati
    { wch: 15 }, // Tahmini Varış
    { wch: 12 }, // Öğrenci Sayısı
    { wch: 50 }, // Öğrenciler
    { wch: 15 }, // Durum
  ];
  ws["!cols"] = colWidths;

  XLSX.utils.book_append_sheet(wb, ws, "Görevlendirmeler");

  // Create detailed sheet with student information
  const detailedData: any[] = [];
  assignments.forEach((item) => {
    const { assignment, vehicle, driver, students } = item;
    students.forEach((student) => {
      detailedData.push({
        "Tarih": format(parseISO(assignment.date), "dd.MM.yyyy", { locale: tr }),
        "Araç": vehicle?.name || "Bilinmeyen",
        "Plaka": vehicle?.plateNumber || "-",
        "Şoför": driver?.name || "Atanmamış",
        "Alış Saati": format(parseISO(assignment.pickupTime), "HH:mm", { locale: tr }),
        "Tahmini Varış": format(parseISO(assignment.estimatedDropoffTime), "HH:mm", { locale: tr }),
        "Öğrenci Adı": student.name,
        "Öğrenci No": student.studentNumber || "-",
        "Email": student.email,
        "Adres": student.homeAddress || "-",
        "Durum": getStatusLabel(assignment.status),
      });
    });
  });

  if (detailedData.length > 0) {
    const wsDetailed = XLSX.utils.json_to_sheet(detailedData);
    const colWidthsDetailed = [
      { wch: 12 }, { wch: 15 }, { wch: 12 }, { wch: 20 },
      { wch: 12 }, { wch: 15 }, { wch: 20 }, { wch: 15 },
      { wch: 25 }, { wch: 40 }, { wch: 15 },
    ];
    wsDetailed["!cols"] = colWidthsDetailed;
    XLSX.utils.book_append_sheet(wb, wsDetailed, "Öğrenci Detayları");
  }

  // Generate filename
  const formattedDate = format(parseISO(date), "yyyy-MM-dd", { locale: tr });
  const filename = `sofor_gorevlendirmeleri_${formattedDate}.xlsx`;

  // Write file
  XLSX.writeFile(wb, filename);
};

/**
 * Export driver assignments to PDF
 * Note: This is a simplified version. For production, consider using jsPDF or react-pdf
 */
export const exportDriverAssignmentsToPDF = async (
  assignments: AssignmentWithDetails[],
  date: string
): Promise<void> => {
  // For now, we'll create a simple HTML-based PDF using browser's print functionality
  // In production, you might want to use jsPDF or react-pdf for better control

  const htmlContent = generatePDFHTML(assignments, date);
  
  // Create a temporary window and print
  const printWindow = window.open("", "_blank");
  if (!printWindow) {
    throw new Error("Popup blocked. Please allow popups for this site.");
  }

  printWindow.document.write(htmlContent);
  printWindow.document.close();
  
  // Wait for content to load, then print
  printWindow.onload = () => {
    setTimeout(() => {
      printWindow.print();
      // Optionally close after printing
      // printWindow.close();
    }, 250);
  };
};

/**
 * Generate HTML content for PDF export
 */
const generatePDFHTML = (
  assignments: AssignmentWithDetails[],
  date: string
): string => {
  const formattedDate = format(parseISO(date), "dd MMMM yyyy", { locale: tr });
  
  let html = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>Şoför Görevlendirmeleri - ${formattedDate}</title>
      <style>
        body {
          font-family: Arial, sans-serif;
          margin: 20px;
          color: #333;
        }
        h1 {
          text-align: center;
          color: #3F51B5;
          margin-bottom: 10px;
        }
        .date {
          text-align: center;
          color: #666;
          margin-bottom: 30px;
        }
        table {
          width: 100%;
          border-collapse: collapse;
          margin-bottom: 30px;
        }
        th, td {
          border: 1px solid #ddd;
          padding: 8px;
          text-align: left;
        }
        th {
          background-color: #3F51B5;
          color: white;
          font-weight: bold;
        }
        tr:nth-child(even) {
          background-color: #f2f2f2;
        }
        .assignment-card {
          page-break-inside: avoid;
          margin-bottom: 20px;
          border: 2px solid #3F51B5;
          padding: 15px;
          border-radius: 5px;
        }
        .assignment-header {
          font-weight: bold;
          color: #3F51B5;
          margin-bottom: 10px;
          font-size: 16px;
        }
        .assignment-details {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 10px;
          margin-bottom: 10px;
        }
        .students-list {
          margin-top: 10px;
        }
        .student-badge {
          display: inline-block;
          background-color: #e3f2fd;
          padding: 4px 8px;
          margin: 2px;
          border-radius: 3px;
          font-size: 12px;
        }
        @media print {
          body { margin: 0; }
          .assignment-card { page-break-inside: avoid; }
        }
      </style>
    </head>
    <body>
      <h1>Şoför Görevlendirmeleri</h1>
      <div class="date">${formattedDate}</div>
  `;

  // Summary table
  html += `
    <table>
      <thead>
        <tr>
          <th>Araç</th>
          <th>Plaka</th>
          <th>Şoför</th>
          <th>Alış Saati</th>
          <th>Tahmini Varış</th>
          <th>Öğrenci Sayısı</th>
          <th>Durum</th>
        </tr>
      </thead>
      <tbody>
  `;

  assignments.forEach((item) => {
    const { assignment, vehicle, driver, students } = item;
    html += `
      <tr>
        <td>${vehicle?.name || "Bilinmeyen"}</td>
        <td>${vehicle?.plateNumber || "-"}</td>
        <td>${driver?.name || "Atanmamış"}</td>
        <td>${format(parseISO(assignment.pickupTime), "HH:mm", { locale: tr })}</td>
        <td>${format(parseISO(assignment.estimatedDropoffTime), "HH:mm", { locale: tr })}</td>
        <td>${students.length}</td>
        <td>${getStatusLabel(assignment.status)}</td>
      </tr>
    `;
  });

  html += `
      </tbody>
    </table>
  `;

  // Detailed cards
  assignments.forEach((item) => {
    const { assignment, vehicle, driver, students } = item;
    html += `
      <div class="assignment-card">
        <div class="assignment-header">
          ${vehicle?.name || "Bilinmeyen Araç"} ${vehicle?.plateNumber ? `(${vehicle.plateNumber})` : ""}
        </div>
        <div class="assignment-details">
          <div><strong>Şoför:</strong> ${driver?.name || "Atanmamış"}</div>
          <div><strong>Alış Saati:</strong> ${format(parseISO(assignment.pickupTime), "HH:mm", { locale: tr })}</div>
          <div><strong>Tahmini Varış:</strong> ${format(parseISO(assignment.estimatedDropoffTime), "HH:mm", { locale: tr })}</div>
          <div><strong>Kapasite:</strong> ${students.length} / ${vehicle ? vehicle.seatingCapacity + vehicle.wheelchairCapacity : "-"}</div>
          <div><strong>Durum:</strong> ${getStatusLabel(assignment.status)}</div>
        </div>
        <div class="students-list">
          <strong>Öğrenciler:</strong><br>
          ${students.map((s) => `<span class="student-badge">${s.name}${s.studentNumber ? ` (${s.studentNumber})` : ""}</span>`).join("")}
        </div>
      </div>
    `;
  });

  html += `
    </body>
    </html>
  `;

  return html;
};

/**
 * Get status label in Turkish
 */
const getStatusLabel = (status: RouteAssignment["status"]): string => {
  const labels: Record<RouteAssignment["status"], string> = {
    scheduled: "Planlandı",
    in_progress: "Devam Ediyor",
    completed: "Tamamlandı",
    cancelled: "İptal Edildi",
  };
  return labels[status] || status;
};

