# Panduan Pengguna Project Billing

**Penagihan termin proyek di ERPNext**

Versi panduan: 11 September 2026 · Untuk user Sales dan Administrasi/Finance

## 1. Kegunaan fitur

Project Billing membantu menagihkan proyek secara bertahap, misalnya DP 50% dan pelunasan 50%. Sales Order (SO) tetap memuat barang, jumlah, dan harga kontrak asli. Setiap termin dibuat menjadi Sales Invoice tersendiri sesuai nilai termin.

Tanggal pembayaran setiap termin belum perlu ditentukan saat membuat SO. User menentukan kapan invoice dibuat; jatuh tempo dihitung dari tanggal invoice ditambah jumlah hari yang diatur pada termin.

**Alur kerja:** Quotation → Sales Order dengan termin → Invoice DP → Pembayaran DP → Delivery Note → Invoice pelunasan → Pembayaran pelunasan.

Invoice, pembayaran, dan pengiriman tetap memakai dokumen ERPNext. Fitur ini tidak otomatis mengirim invoice ke customer atau mencatat uang masuk.

## 2. Persiapan

Pastikan administrator sudah mengaktifkan Project Billing dan menentukan item penagihan nonstok. Contoh nama item: **PB-TERMIN: Penagihan Termin Proyek**; sesuaikan dengan konfigurasi perusahaan.

User memerlukan akses sesuai pekerjaannya: Sales Order untuk order, Sales Invoice untuk tagihan, Payment Entry untuk pembayaran, dan Delivery Note untuk pengiriman. Jika menu atau tombol tidak tersedia, hubungi administrator untuk memeriksa hak akses.

Contoh nama template: **Project DP 50 - Pelunasan 50**. Administrator perlu menyiapkannya sebelum dapat dipilih oleh pengguna.

### Membuat template baru — untuk user yang berwenang

1. Cari **Project Billing Template** melalui kolom pencarian ERPNext.
2. Klik **New**, lalu isi **Template Name**.
3. Tambahkan baris pada tabel **Installments** seperti contoh berikut.
4. Pastikan total porsi 100%, kemudian **Save**.

| Field | Baris DP | Baris pelunasan |
|---|---|---|
| Term Code | DP | FINAL |
| Description | DP | Pelunasan |
| Invoice Portion (%) | 50 | 50 |
| Days After Invoice Date | 0 | 14 |
| Payment Required Before Delivery | Dicentang | Tidak dicentang |

**Term Code** adalah kode unik untuk setiap termin dalam satu template. **Days After Invoice Date** berisi jumlah hari, bukan tanggal kalender. Nilai 0 berarti jatuh tempo pada tanggal invoice.

Jika opsi pemeriksaan pembayaran sebelum pengiriman diaktifkan oleh administrator, total termin yang dicentang **Payment Required Before Delivery** menjadi batas minimum pembayaran sebelum Delivery Note dapat disubmit. Pemeriksaan memakai jumlah pembayaran teralokasi secara kumulatif.

Template ini berbeda dari **Payment Terms Template** bawaan ERPNext. Untuk fitur termin proyek, pilih **Project Billing Template**.

## 3. Membuat Sales Order dengan termin

1. Buat dan submit **Quotation** dengan customer, barang, qty, harga, dan pajak yang sesuai kesepakatan.
2. Dari Quotation, gunakan **Create → Sales Order**. SO juga dapat dibuat langsung sesuai prosedur perusahaan.
3. Saat SO masih **Draft**, periksa company, customer, barang, qty, harga, pajak, warehouse, dan tanggal pengiriman yang dibutuhkan ERPNext.
4. Pada bagian **Project Billing** di area pembayaran SO, centang **Use Project Installments**.
5. Pilih **Project Billing Template**. Tabel **Project Installments** akan terisi dari template.
6. Periksa porsi, jumlah hari jatuh tempo, dan penanda pembayaran sebelum pengiriman. Total porsi wajib 100%.
7. Klik **Save**, periksa kembali, kemudian **Submit**.

Ketika fitur termin diaktifkan, jadwal Payment Terms bawaan disembunyikan dan dikosongkan pada draft SO. Gunakan tabel **Project Installments** untuk skema proyek ini.

**Contoh:** kontrak Rp10.000.000 termasuk pajak, DP 50%, pelunasan 50%. Masing-masing tagihan bernilai Rp5.000.000. SO tidak membutuhkan tanggal invoice pelunasan saat dibuat; tanggal pengiriman yang diwajibkan ERPNext tetap harus diisi.

Periksa kontrak sebelum submit. Perubahan nilai atau tambahan proyek pada alur ini dibuat sebagai **SO baru**.

## 4. Membuat invoice DP

1. Buka SO yang sudah **Submitted**.
2. Pilih **Project Billing → Create Installment Invoice**.
3. Pada **Installment**, pilih **DP (50%)**.
4. Isi **Invoice Date** sesuai tanggal penerbitan tagihan.
5. Klik **Create Draft**. Sistem membuka draft Sales Invoice.
6. Periksa customer, company, tanggal, **Payment Due Date**, informasi **Penagihan Termin**, pajak, dan **Grand Total**.
7. Jika siap menjadi tagihan resmi, klik **Submit** sesuai kewenangan user.

Tanggal jatuh tempo mengikuti pengaturan termin. Contoh: invoice pelunasan bertanggal 11 September 2026 dengan 14 hari akan jatuh tempo 25 September 2026.

**Create Draft belum membukukan tagihan dan belum mencatat pembayaran.** Jika termin yang sama sudah memiliki invoice aktif, tombol pembuatan membuka invoice tersebut, bukan membuat duplikat. Tombol ini digunakan untuk seluruh invoice termin pada SO, termasuk pelunasan.

### Memahami tampilan invoice

| Bagian | Kegunaan |
|---|---|
| Customer, Company, tanggal | Informasi bawaan Sales Invoice |
| Penagihan Termin | Link SO, nama termin, persentase, dan nilai kontrak termasuk pajak |
| Referensi Barang Kontrak | Klik judulnya untuk membuka rincian barang, qty, dan harga asli SO |
| Items | Baris tagihan termin yang dipakai untuk menghitung invoice |
| Taxes and Charges | Pajak pada tagihan tersebut |
| Grand Total | Total nilai invoice termin yang diterbitkan |

### Mengapa Items berisi PB-TERMIN?

**PB** berarti **Project Billing**. Item nonstok ini mewakili nilai tagihan termin. Setiap baris barang SO memperoleh satu baris tagihan yang tetap terhubung ke barang asalnya.

Misalnya nilai barang sebelum pajak Rp900.000, Rp800.000, dan Rp1.600.000. Pada DP 50%, baris PB-TERMIN menjadi Rp450.000, Rp400.000, dan Rp800.000. Total sebelum pajak Rp1.650.000; dengan pajak 11% dalam contoh ini, Grand Total Rp1.831.500. Tarif aktual mengikuti dokumen perusahaan.

Qty 1 pada baris PB-TERMIN merupakan satu baris tagihan, bukan jumlah barang yang dikirim. Jangan mengganti item, qty, rate, atau pajak untuk memaksa nilai termin berbeda. Rincian barang asli tersedia di SO dan **Referensi Barang Kontrak**.

## 5. Mencetak proforma atau invoice resmi

Pada Sales Invoice termin, pilih **View → Print Installment Invoice**. Tombol ini membuka format cetak **Project Installment Invoice**, yang menampilkan referensi barang kontrak dan nilai tagihan termin.

- **Draft:** format cetak menampilkan judul **PROFORMA INVOICE**. Pencetakan draft harus diizinkan pada pengaturan ERPNext.
- **Submitted:** gunakan sebagai invoice yang sudah disubmit dan dibukukan.

Proforma menggunakan draft Sales Invoice yang sama; tidak ada dokumen proforma terpisah. Setelah disetujui, submit draft tersebut sesuai prosedur perusahaan.

Pencetakan tidak otomatis mengirim dokumen kepada customer. Simpan sebagai PDF melalui fasilitas cetak yang tersedia, lalu kirim sesuai prosedur administrasi. Jika memilih format melalui ikon printer bawaan, pilih **Project Installment Invoice** untuk mendapatkan rincian cetak termin.

## 6. Mencatat pembayaran DP

Alur harian yang digunakan panduan ini: submit invoice DP terlebih dahulu, lalu catat pembayarannya.

1. Buka invoice DP yang sudah disubmit.
2. Pilih **Create → Payment** untuk membuka Payment Entry sesuai menu dan hak akses ERPNext.
3. Periksa customer, tanggal pembayaran, rekening/kas penerima, jumlah uang yang benar-benar diterima, serta referensi transaksi.
4. Pada tabel **References**, pastikan pembayaran dialokasikan ke invoice DP yang benar dengan nominal yang tepat.
5. **Save**, periksa, kemudian **Submit** Payment Entry.
6. Kembali ke SO dan pilih **Project Billing → Refresh Payments** untuk melihat ringkasan terbaru.

Payment Entry yang masih draft belum dihitung sebagai pembayaran diterima. Uang customer yang belum dialokasikan ke SO atau invoice terkait juga belum dihitung sebagai pembayaran proyek tersebut.

Jika DP belum dibayar penuh, catat sesuai penerimaan aktual. Pengiriman dapat tetap tertahan sampai nilai pembayaran memenuhi batas yang diwajibkan.

## 7. Mengirim barang setelah DP

1. Pastikan pembayaran DP sudah tercatat dan dialokasikan dengan benar.
2. Buka **Sales Order**, lalu pilih **Create → Delivery Note**.
3. Periksa barang asli, qty yang benar-benar dikirim, warehouse, tanggal, dan data pengiriman lainnya.
4. **Save**, periksa, kemudian **Submit** Delivery Note.

Buat pengiriman dari **SO**, bukan dari item PB-TERMIN pada invoice. Jangan memakai **Update Stock** pada invoice termin; pengeluaran barang dilakukan melalui Delivery Note.

Jika pemeriksaan pembayaran sebelum pengiriman aktif dan dana teralokasi belum mencukupi, sistem menolak submit Delivery Note. Periksa Payment Entry dan alokasinya terlebih dahulu.

## 8. Menagih dan menerima pelunasan

Saat proyek sudah waktunya ditagih lagi menurut kesepakatan customer:

1. Buka SO yang sama.
2. Pilih **Project Billing → Create Installment Invoice**.
3. Pilih termin **Pelunasan**, isi tanggal invoice, lalu **Create Draft**.
4. Periksa nominal dan jatuh tempo, lalu cetak proforma atau submit invoice sesuai kebutuhan.
5. Kirim tagihan melalui prosedur administrasi perusahaan.
6. Setelah uang diterima, buat dan submit **Payment Entry** yang dialokasikan ke invoice pelunasan.
7. Gunakan **Refresh Payments** pada SO dan periksa seluruh nilai pembayaran.

Pembuatan termin dilakukan oleh user saat diperlukan. Tidak ada proses persetujuan milestone tambahan di app ini.

## 9. Membaca ringkasan pembayaran SO

| Field | Arti |
|---|---|
| Total Ditagih | Total invoice termin yang sudah disubmit, termasuk pajak; draft dan cancelled tidak dihitung |
| Belum Ditagih | Nilai kontrak yang belum menjadi invoice submitted |
| Pembayaran Diterima | Pembayaran submitted yang sudah dialokasikan ke SO atau invoice terkait |
| Outstanding Invoice | Saldo belum terselesaikan pada invoice submitted; bukan sisa seluruh kontrak |
| Status Pembayaran | Status pembayaran proyek secara keseluruhan |
| Payment Summary Updated | Waktu pembaruan terakhir |

### Contoh kontrak Rp10 juta, DP 50% dan pelunasan 50%

| Tahap | Ditagih | Diterima | Belum ditagih | Outstanding invoice | Status pembayaran |
|---|---:|---:|---:|---:|---|
| SO disubmit, belum ada invoice | Rp0 | Rp0 | Rp10 juta | Rp0 | Unpaid |
| Invoice DP disubmit, belum dibayar | Rp5 juta | Rp0 | Rp5 juta | Rp5 juta | Unpaid |
| DP lunas, barang sudah dikirim | Rp5 juta | Rp5 juta | Rp5 juta | Rp0 | Partly Paid |
| Invoice pelunasan disubmit, belum dibayar | Rp10 juta | Rp5 juta | Rp0 | Rp5 juta | Partly Paid |
| Semua invoice lunas | Rp10 juta | Rp10 juta | Rp0 | Rp0 | Paid |

**Outstanding Invoice Rp0 belum tentu berarti proyek lunas.** Periksa juga **Belum Ditagih**, **Pembayaran Diterima**, dan **Status Pembayaran**.

Status SO bawaan tetap mengikuti ERPNext. SO dapat **Completed** ketika penagihan dan pengiriman sudah 100%, meskipun pembayaran masih sebagian. Gunakan field **Status Pembayaran** untuk memeriksa pelunasan.

Jika status **Settled with Adjustments** muncul, saldo telah terselesaikan dengan penyesuaian dan bukan seluruhnya penerimaan uang. Minta Finance memeriksa dokumen terkait. Status **Cancelled** menunjukkan SO dibatalkan.

## 10. Ringkasan menu

| Lokasi | Menu | Fungsi |
|---|---|---|
| Sales Order → Project Billing | Refresh Payments | Menghitung ulang ringkasan; tidak membuat pembayaran |
| Sales Order → Project Billing | Installment Invoices | Membuka daftar invoice termin SO tersebut |
| Sales Order → Project Billing | Create Installment Invoice | Membuat atau membuka invoice aktif untuk termin yang dipilih |
| Sales Invoice → View | Project Sales Order | Membuka SO asal invoice termin |
| Sales Invoice → View | Print Installment Invoice | Membuka format cetak termin |

## 11. Kesalahan dan pembatalan

| Situasi | Tindakan user |
|---|---|
| Tombol Create Installment Invoice tidak ada | Periksa fitur termin aktif, SO submitted, tidak Closed/On Hold/Cancelled, dan akses membuat Sales Invoice |
| Ringkasan pembayaran belum berubah | Pastikan Payment Entry submitted dan alokasinya benar, lalu Refresh Payments |
| Outstanding Rp0 tetapi pembayaran masih sebagian | Periksa Belum Ditagih; mungkin invoice pelunasan belum dibuat |
| Pembuatan termin membuka invoice lama | Invoice aktif sudah ada; lanjutkan dokumen tersebut |
| Invoice draft salah | Periksa dan koreksi bagian yang diizinkan; bila perlu hapus draft sesuai hak akses lalu buat ulang termin |
| Invoice submitted salah | Ikuti proses Cancel ERPNext; pembayaran/dokumen terkait mungkin perlu ditangani terlebih dahulu oleh Finance. Setelah cancelled, termin dapat dibuat ulang |
| Pembayaran salah | Finance membatalkan dan memperbaiki Payment Entry sesuai aturan ERPNext, lalu periksa ulang ringkasan SO |
| Pengiriman ditolak | Periksa jumlah pembayaran teralokasi dan syarat sebelum pengiriman |
| Muncul penolakan pajak, pembulatan, atau konfigurasi | Catat pesan dan nomor SO/invoice, lalu hubungi administrator; jangan mengubah nominal sembarang agar lolos |

Invoice submitted tidak dihapus langsung sebagai pengganti proses pembatalan. Perubahan nilai proyek dibuat pada SO baru. Retur/credit note belum termasuk alur fitur ini.

## 12. Checklist sebelum selesai

- Customer, company, barang, nilai kontrak, dan skema termin benar.
- Setiap tagihan yang diterbitkan menggunakan termin yang tepat.
- Invoice resmi sudah disubmit; proforma masih draft sesuai kebutuhan.
- Pembayaran sesuai uang yang diterima dan dialokasikan ke dokumen yang tepat.
- Delivery Note memuat barang asli dan qty pengiriman aktual.
- Untuk proyek lunas: Belum Ditagih Rp0, Outstanding Invoice Rp0, dan Status Pembayaran Paid.

Jika ada masalah, sampaikan nomor SO, nomor invoice/Payment Entry terkait, langkah yang dilakukan, dan pesan error kepada administrator.
