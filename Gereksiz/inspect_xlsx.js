const XLSX = require('xlsx');
const path = require('path');

const filePath = path.resolve('Veri.xlsx');
const workbook = XLSX.readFile(filePath);

console.log('Sheets:', workbook.SheetNames);

workbook.SheetNames.forEach(sheetName => {
    if (sheetName === 'Pick' || sheetName === 'Drop') {
        const sheet = workbook.Sheets[sheetName];
        const data = XLSX.utils.sheet_to_json(sheet, { header: 1 });

        console.log(`\n--- Sheet: ${sheetName} ---`);
        console.log('Header Row:', data[0].slice(0, 15)); // Show first 15 columns
        console.log('Sample Row 1:', data[1]?.slice(0, 15));
        console.log('Sample Row 2:', data[2]?.slice(0, 15));

        // Find column indices for student codes
        const headers = data[0];
        const ogrenciIdx = headers.indexOf('Ogrenci');
        console.log('Ogrenci column index:', ogrenciIdx);
    }
});
