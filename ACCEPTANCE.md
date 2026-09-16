# Server testing acceptance

Gunakan data testing dan simpan nomor dokumen/bukti setiap hasil. Jangan mengirim email customer sungguhan. Matriks ini tetap menjadi checklist lengkap untuk setiap deployment; jangan menganggap seluruh baris lolos hanya karena sebagian tes sudah lulus.

| Skenario | Hasil yang perlu dibuktikan |
|---|---|
| Install/migrate dua kali | Custom fields/DocTypes/print format tersedia tanpa duplikasi; akun dan core file tetap |
| SO dari Quotation | Qty/rate barang sama; template termin 50/50 atau 50/30/20 tanpa due date dapat disimpan/submit |
| Invoice DP | Grand total 50% termasuk pajak; qty/rate kontrak utuh pada tabel referensi; native invoice item jasa |
| Proforma | Draft print berlabel PROFORMA; tidak ada GL; belum masuk Total Ditagih |
| Invoice DP submit | GL seimbang, piutang/pendapatan/pajak sesuai konfigurasi; SO per_billed 50% |
| Belum bayar DP | Submit Delivery Note dari SO ditolak jika enforcement aktif |
| Sudah bayar DP | Payment Entry aktual; DN original goods dapat submit; SO 100% delivered, 50% billed, Partly Paid |
| Invoice final belum bayar | SO native Completed jika delivered/billed penuh; pembayaran masih Partly Paid; outstanding sebesar final |
| Pelunasan | Kedua invoice outstanding nol, received total sama kontrak, status Paid |
| 50/30/20 | Invoice sesuai tiga porsi dan due date masing-masing; urutan pembuatan invoice tidak mengubah rounding porsi |
| Pajak | On Net Total exclusive/inclusive dan Actual; total semua invoice sama kontrak; GL/tax account benar |
| Rounding ekstrem | Nilai kecil dan beberapa baris; jika target tidak tercapai ditolak tanpa draft/GL parsial |
| Klik ganda/concurrent requests | Dua request bersamaan untuk SO/termin sama hanya menghasilkan satu invoice aktif, termasuk insert via REST |
| Izin | User tanpa SI create tidak bisa generate; user tanpa baca SO tidak dapat akses order; ordinary invoice tetap memakai permission native |
| Bypass | Invoice dibuat dari DN/native SO mapper atau field REST yang menghapus marker tidak dapat menagih managed SO di luar termin |
| Cancel/amend/delete | Payment cancel dulu jika wajib; cancel SI mengembalikan per_billed/ringkasan; draft delete/cancel melepas termin; amend tetap tervalidasi |
| Advance SO → reconcile SI | Received tidak dihitung dua kali; outstanding native benar; refresh manual dan scheduler memperbarui field |
| Payment cancel/reconcile ulang | Total received berkurang/berpindah ke order tepat; tidak tersisa saldo cache lama |
| Adjustment | Write-off tidak dihitung sebagai kas; settled adjustment tampil terpisah; deductions PE ditolak |
| List View | Native status tetap; tambah kolom payment status, outstanding dan unbilled, lalu filter |
| Kontrak tetap | Update Items setelah submit tidak dapat mengganti qty/rate/nilai; perubahan proyek memakai SO baru |
| Regresi ordinary documents | SO/SI/PE/DN biasa tetap dapat digunakan tanpa Project Billing |
| Update app / ERPNext patch | Ulangi smoke dan integrasi; review diff method native yang dioverride |

Jika ditemukan perbedaan, perbaiki app lalu ulangi skenario terdampak. Jangan menyatakan instalasi berhasil sebagai bukti seluruh akuntansi benar.
