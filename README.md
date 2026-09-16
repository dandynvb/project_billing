# Project Billing — ERPNext v15

Custom app untuk penagihan termin proyek pada Frappe/ERPNext **v15**. Source tidak menyertakan konfigurasi site, credential, data customer, screenshot operasional, atau paket build lama. Setiap deployment baru tetap perlu menjalankan skenario penerimaan sesuai konfigurasi perusahaan.

## Panduan untuk user

Lihat [Panduan Pengguna](docs/PANDUAN_PENGGUNA.md) untuk alur harian administrasi dari SO sampai pelunasan. Panduan bergambar dan bukti pengujian dari site tertentu disimpan terpisah dari repository.

## Alur yang diimplementasikan

1. Quotation dan Sales Order memakai barang, qty, dan harga kontrak asli.
2. Pada draft SO, aktifkan **Use Project Installments**, lalu pilih **Project Billing Template**. Contoh DP 50% dan pelunasan 50%, atau 50/30/20. Total porsi wajib 100%.
3. Tabel termin tidak membutuhkan tanggal jatuh tempo. `Credit Days` dihitung dari tanggal invoice yang dibuat kemudian. Admin menentukan kapan membuat invoice; tidak ada milestone approval.
4. Setelah SO submit, pilih **Project Billing → Create Installment Invoice**, termin, dan tanggal. App membuat **draft Sales Invoice ERPNext**. Klik ulang membuka invoice aktif yang sama.
5. Cetak dengan **Project Installment Invoice**. Draft diberi judul PROFORMA INVOICE. Ini draft SI yang sama, bukan doctype proforma terpisah. Pengaturan ERPNext untuk mengizinkan print draft tetap berlaku.
6. Submit Sales Invoice untuk membukukan tagihan. Catat pembayaran melalui Payment Entry ERPNext. App tidak otomatis submit, membayar, atau mengirim email.
7. Buat Delivery Note **dari SO**, untuk barang asli. Jika pengaturan enforcement aktif, jumlah pembayaran teralokasi ke SO/invoicenya harus mencapai total termin bertanda **Payment Required Before Delivery** sebelum DN dapat disubmit. Penanda ini memeriksa nilai pembayaran kumulatif, bukan approval milestone atau urutan nomor invoice.
8. Buat invoice termin berikutnya saat perlu menagih. Invoice pelunasan yang belum dibayar tetap menambah piutang.

## Informasi pembayaran berupa field SO

| Field | Makna |
|---|---|
| Total Ditagih | Jumlah invoice termin submitted, termasuk pajak; draft/cancelled tidak dihitung |
| Belum Ditagih | Nilai kontrak dikurangi total invoice submitted |
| Pembayaran Diterima | Payment Entry submitted yang dialokasikan ke SO atau invoice terkait; advance tidak dihitung dua kali setelah referensinya direkonsiliasi |
| Outstanding Invoice | Jumlah outstanding pada invoice submitted, bukan sisa seluruh kontrak |
| Status Pembayaran | Unpaid, Partly Paid, Paid, Settled with Adjustments, atau Cancelled |
| Payment Summary Updated | Waktu pembaruan ringkasan terakhir |

Contoh kontrak Rp10 juta: invoice DP Rp5 juta sudah dibayar, barang telah dikirim, invoice pelunasan belum dibuat → **ditagih Rp5 juta, belum ditagih Rp5 juta, pembayaran Rp5 juta, outstanding invoice Rp0, status Partly Paid**. Setelah invoice pelunasan Rp5 juta disubmit, outstanding invoice menjadi Rp5 juta.

Status bawaan SO tetap milik ERPNext. App tidak menulis `status`, `per_billed`, atau `per_delivered` sendiri. Baris invoice ditautkan ke SO Item agar updater ERPNext menghitung persentase penagihan. Target pengujian: SO dapat Completed ketika pengiriman dan penagihan 100%, sementara field pembayaran masih Partly Paid.

Field ringkasan tersedia bagi pengguna yang memiliki akses baca SO tersebut; ini memang memperluas informasi pembayaran yang terlihat dari SO. Nomor/detail invoice tetap memakai izin Sales Invoice. Kolom tambahan tersedia melalui pengaturan kolom List View; indikator status native dipertahankan.

Pembayaran diperbarui lewat event invoice/payment dan antrean setelah commit. Rekonsiliasi ERPNext yang mengubah data langsung melalui SQL juga diperbaiki oleh scheduler per jam. Gunakan **Refresh Payments** untuk memeriksa saat itu juga; worker/scheduler harus aktif. Uang customer yang belum dialokasikan tidak dihitung sebagai pembayaran proyek. Journal Entry/write-off bukan penerimaan kas dalam ringkasan ini.

## Print Format SI JSI

[SI JSI](docs/PRINT_FORMAT_SI_JSI.md) mengikuti style PO JSI dan memakai Print Format Builder dengan Custom Format tidak dicentang. DP/progress satu baris; pelunasan seluruh barang SO, pembayaran diterima, serta saldo invoice berwarna merah. Pilih jenis termin pada template/SO; Auto menjaga kompatibilitas dokumen lama. Shortcut Print Installment Invoice membuka SI JSI.

## Model invoice dan pembukuan

Invoice tetap Sales Invoice ERPNext. Setiap baris SO mendapat satu baris item jasa non-stock penagihan termin dengan qty 1 dan nilai porsi termin. Tabel **Original Contract Items** menyimpan rincian barang asli dengan qty/harga utuh, dan ikut dicetak sebagai referensi kontrak. Baris referensi tidak dibukukan lagi.

Konsekuensi: laporan penjualan per item invoice menampilkan **item penagihan**, sedangkan rincian barang ada pada SO/DN/tabel kontrak. SI submit menggunakan akun pendapatan/piutang/pajak dan aturan posting native. Ini bukan implementasi deferred revenue atau pengakuan pendapatan berdasarkan milestone. Akun yang dipilih perlu diperiksa dalam uji server bersama administrasi perusahaan.

App menyesuaikan `SalesInvoice.validate_with_previous_doc` melalui `override_doctype_class` supaya item penagihan boleh berbeda dari item barang pada SO, dengan validasi referensi dan nilai porsi pengganti. Invoice biasa meneruskan validasi native. Tidak ada core file ERPNext/Frappe yang diubah. Karena v15 hanya memilih satu override efektif, instalasi ditolak jika app lain juga override kelas Sales Invoice; kompatibilitas perlu direview dahulu.

## Batas versi 0.1

- Ditargetkan ke Frappe/ERPNext **v15**; rujukan source yang diperiksa: Frappe 15.114.0 dan ERPNext 15.115.0. Versi mayor lain ditolak. Patch lain tetap perlu regression test.
- Mata uang SO harus mata uang company dengan conversion rate 1. Invoice account currency juga harus sama. Belum mendukung kontrak multi-currency.
- Porsi item dibulatkan secara kumulatif supaya seluruh termin menjumlah ke nilai kontrak. Pajak dihitung oleh ERPNext. Jika hasil pajak native tidak persis sama dengan target porsi termasuk pajak, invoice ditolak dengan pesan jelas. Penanganan selisih rounding khusus belum diimplementasikan; jangan mengubah pajak untuk melewati validasi.
- Mendukung pajak penjualan positif **On Net Total** (termasuk harga inclusive) dan **Actual** yang dibagi per termin. Belum mendukung pajak bertingkat, item-specific tax template, withholding, diskon tambahan tingkat header, atau perbedaan rounded total dari grand total. Diskon item asli sudah tercermin dalam amount kontrak.
- Payment Entry dengan deductions/payment taxes ditolak untuk alokasi proyek; gunakan alur adjustment terpisah. Saldo hasil write-off bukan kas. Rekonsiliasi advance, pembatalan pembayaran, rounding pajak, dan kondisi simultan tetap wajib diuji di server.
- Tidak mendukung retur/credit note, POS, stock update dari invoice termin, drop shipment, atau inter-company. DN mengirim barang SO asli.
- Jika Selling Settings mewajibkan Delivery Note untuk setiap invoice, atur pengecualian customer yang sesuai lewat konfigurasi ERPNext sebelum menguji DP; app tidak mematikan kebijakan site tersebut.
- Kontrak yang sudah submit tidak dapat diubah qty/rate/nilainya lewat app. Tambahan proyek dibuat SO baru.
- Cancel invoice mengikuti aturan ERPNext, termasuk membatalkan/unlink pembayaran lebih dulu bila diwajibkan. Setelah cancelled, termin dapat dibuat ulang. Draft yang dihapus melepas reservasi termin. Amend mempertahankan penanda kontrak dan tetap divalidasi; bukan jalan untuk mengganti nilai termin.
- Jangan mengubah billing item saat masih ada draft termin yang memakai item lama; draft lama akan ditolak karena tidak cocok dengan konfigurasi.

## Instalasi pada server testing

Perlu SSH/Bench atau operator server; REST API key saja tidak memasang Python app. Simpan credential di luar direktori ini. Belum ada credential di paket app.

1. Backup site testing dan periksa versi serta daftar app/override aktif.
2. Salin folder ini ke server. Dari direktori Bench, daftarkan source lokal dengan `bench get-app /absolute/path/to/project_billing` (direktori source harus Git repository; jalankan `git init` dan buat commit lokal bila belum). Atau gunakan URL Git repo yang memang sudah disiapkan sendiri.
3. Jalankan perintah berikut, ganti `TEST_SITE` dengan nama site testing:

```sh
bench --site TEST_SITE install-app project_billing
bench --site TEST_SITE migrate
bench build --app project_billing
bench restart
```

Untuk Bench dalam container, masukkan app ke image/deployment yang persisten dan jalankan restart dengan mekanisme deployment tersebut.

4. Buka **Project Billing Settings** sebagai System Manager. Pilih item jasa penagihan: non-stock, sales item aktif, tanpa deferred revenue/item tax template. App tidak membuat atau mengganti company, customer, item, akun, ataupun tarif pajak otomatis.
5. Buat template DP 50% (required before delivery), pelunasan 50%; isi credit days masing-masing tanpa tanggal. Aktifkan Project Billing.
6. Ikuti [skenario penerimaan](ACCEPTANCE.md) pada server testing sebelum produksi. Instalasi ulang/migrate mengupdate field dan print format milik app. Duplikat print format jika hendak membuat format cetak sendiri.

Uninstall diblokir selama ada draft/submitted invoice termin. Membatalkan semua invoice bukan rekomendasi migrasi data; rencanakan retensi dan pemindahan data sebelum melepas app.

## Pengujian

Tes Python tanpa Frappe (rule server menggunakan adapter mock):

```sh
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

Tes integrasi disiapkan di `project_billing/tests/test_integration.py`. Jalankan **hanya pada disposable test site**, dengan app terpasang dan fixture test ERPNext, bukan site operasional. Tes mengubah settings sementara dan membuat dokumen test.

```sh
bench --site TEST_SITE set-config allow_tests true
bench --site TEST_SITE set-config project_billing_test_site true
bench --site TEST_SITE run-tests --app project_billing --module project_billing.tests.test_integration
```

Tes lokal memakai mock Frappe dan tidak menggantikan pengujian integrasi pada ERPNext sesungguhnya. Lihat [panduan deployment](DEPLOYMENT.md) dan [skenario penerimaan](ACCEPTANCE.md). Setiap server/configuration baru tetap perlu acceptance test.

## Rujukan teknis

- [Frappe hooks](https://docs.frappe.io/framework/user/en/python-api/hooks)
- [ERPNext payment terms](https://docs.frappe.io/erpnext/payment-terms)
- [Sales Invoice source v15.115.0](https://github.com/frappe/erpnext/blob/v15.115.0/erpnext/accounts/doctype/sales_invoice/sales_invoice.py)
- [Payment Entry source v15.115.0](https://github.com/frappe/erpnext/blob/v15.115.0/erpnext/accounts/doctype/payment_entry/payment_entry.py)
