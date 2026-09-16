# SI JSI — Print Format Sales Invoice

Dibuat dengan acuan PO JSI pada server testing, 11 September 2026.

## Cara menggunakan

1. Buka Sales Invoice, pilih ikon Print, lalu pilih **SI JSI** pada Print Format.
2. Pilih Letter Head sesuai perusahaan, misalnya **JSI** untuk Jakarta Sistem Integrators. Kop mengikuti pilihan Letter Head/dokumen, tidak dipaksakan oleh format.
3. Untuk invoice termin, **View → Print Installment Invoice** kini membuka SI JSI. Format lama **Project Installment Invoice** tetap tersedia di pemilihan format.
4. Periksa tagihan berwarna merah, lalu cetak/unduh PDF.

Print Format **SI JSI** menggunakan **Print Format Builder**, dengan **Custom Format tidak dicentang** (`custom_format=0`). HTML dan Jinja berada di blok Custom HTML pada `format_data`, seperti PO JSI. Kolom `html` utama kosong.

## Mengedit per bagian

SI JSI memiliki 6 blok HTML terpisah di Print Format Builder, selain Heading:

1. Informasi Invoice — nomor, tanggal, terms, due date.
2. Alamat Bill To dan Ship To.
3. Referensi SO dan Termin.
4. Tabel Item, Total, Pajak, dan Pembayaran — satu tabel utuh; ringkasan memakai colspan 4 dan nominal di kolom terakhir.
5. Catatan Pembayaran.
6. Tanda Tangan.

Klik **Edit HTML** pada blok yang ingin diubah. Setiap blok menyiapkan variabel Jinja sendiri sehingga tidak bergantung pada kode di blok sebelumnya. Label/nama bagian juga ditulis pada komentar awal HTML. File source dipisah menjadi `si_jsi_invoice_info.html`, `si_jsi_addresses.html`, `si_jsi_order_reference.html`, `si_jsi_items.html`, `si_jsi_notes.html`, dan `si_jsi_signature.html`. CSS tetap di `si_jsi.css`.

Alamat Bill To/Ship To menggunakan komponen Address yang digabung dengan koma, seperti PO JSI. Phone/Email tetap di baris terpisah. Jika link Address tidak tersedia, teks alamat dokumen dipakai sebagai fallback. Tabel item dan ringkasan kini berada dalam satu blok `si_jsi_items.html`; area ringkasan diberi komentar RINGKASAN untuk memudahkan edit.

## Jenis termin

Pada tabel termin di Project Billing Template/Sales Order terdapat **Jenis Termin**:

- **DP**: satu baris Pembayaran DP beserta persentasenya.
- **Progress**: satu baris Pembayaran Progress beserta persentasenya; nama tahap tambahan ditampilkan jika tersedia.
- **Pelunasan**: seluruh barang asli dari SO, dengan qty, harga, dan nilai kontrak.
- **Auto**: untuk kompatibilitas dengan SO lama. Berdasarkan urutan tabel: pertama DP, tengah Progress, terakhir Pelunasan. Jika hanya satu termin, dianggap Pelunasan. Auto tidak menebak nama atau urutan tanggal invoice.

Atur jenis termin ketika template/SO masih dapat diedit. SO lama tidak diubah otomatis. Invoice biasa tanpa penanda Project Billing tetap mencetak item invoice normal. Format ini bukan format credit note/retur.

## Arti angka pembayaran

- DP dan Progress: Total/PPN/Grand Total menggunakan nilai invoice termin.
- Progress: pembayaran kontrak selain invoice ini ditampilkan sebagai informasi. Jumlah tersebut **tidak dikurangkan lagi** dari invoice progress.
- Pelunasan: Total/PPN/Grand Total Kontrak memakai nilai SO. Nilai invoice pelunasan ditampilkan terpisah agar nilai kontrak penuh tidak disangka sebagai nilai invoice ini.
- Pembayaran kontrak diambil langsung dari Payment Entry submitted yang dialokasikan ke SO atau invoice submitted terkait. Pembayaran yang belum dialokasikan tidak dihitung; pembatalan pembayaran diperhitungkan saat cetak ulang.
- **Jumlah yang harus dibayarkan — invoice ini** (merah) menggunakan outstanding invoice submitted. Untuk draft, memakai nilai invoice dikurangi advance/paid amount pada draft. Invoice cancelled ditampilkan dengan saldo tagihan 0 jika pencetakan cancelled diizinkan ERPNext.
- Jika sisa nilai kontrak tidak sama dengan outstanding invoice ini, format menampilkan keduanya dan penjelasan; tunggakan invoice terdahulu tidak ditagihkan ulang sebagai invoice pelunasan.
- Informasi pembayaran bersifat **terbaru saat cetak**, bukan snapshot saat penerbitan. Waktu cetak disertakan. Saldo yang diselesaikan dengan adjustment bukan otomatis uang diterima.

Pajak mengikuti baris pajak dokumen, termasuk tarif aktual; label 11% tidak ditulis tetap. Qty pecahan tetap ditampilkan. Untuk harga inclusive/diskon, penyesuaian dari total harga ke nilai sebelum pajak ditampilkan bila diperlukan.

## Style dan pemeliharaan

Style dasar disalin dari Print Style **Redesign 2** yang digunakan PO JSI: font, warna `#5a9cab`, border hitam, alignment nominal, dan area tanda tangan. Tambahan CSS hanya untuk saldo merah, catatan, dan pemenggalan ringkasan/tanda tangan.

Area tanda tangan menampilkan company dan nama pembuat dokumen secara dinamis. Source yang didistribusikan tidak memuat mapping email staf atau file gambar tanda tangan. Untuk memakai gambar tanda tangan, siapkan data privat pada site dan atur pada duplikat print format. Letter Head juga perlu disiapkan pada server tujuan.

Source format berada pada `project_billing/templates/si_jsi*`, installer `project_billing/print_format_setup.py`, dan helper baca pembayaran `project_billing/printing.py`. Helper memeriksa izin Print invoice dan Read SO. Tidak ada API publik baru untuk mengambil ringkasan cetak.

Format dipasang/diperbarui oleh setup app saat install/migrate. **Duplikat SI JSI dengan nama lain** jika ingin mengedit lewat Builder tanpa ditimpa pembaruan app. Nama SI JSI yang sudah dimiliki modul lain menyebabkan instalasi berhenti, bukan ditimpa diam-diam.

PO JSI, Print Style global, transaksi existing, dan core ERPNext tidak diubah oleh pemasangan format ini.

Tampilan alamat Bill To dan Ship To menampilkan Tax ID customer yang sama. Baris SO/termin, waktu pembaruan pembayaran, dan catatan draft di bawah tabel tidak dicetak. Judul Proforma Invoice tetap digunakan untuk draft; informasi Customer PO tetap tampil jika diisi.
