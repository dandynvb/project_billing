# Instalasi Project Billing pada ERPNext v15

Source app ini ditargetkan untuk Frappe dan ERPNext v15. Versi patch dan konfigurasi server tujuan tetap perlu diuji. Jangan memasukkan credential, site_config.json, database backup, atau file customer ke repository.

## Bench biasa

Jalankan dari direktori Bench sebagai user pengelola Bench. Ganti `REPOSITORY_URL` dan `TEST_SITE` sesuai lingkungan tujuan; URL repository di bawah adalah placeholder, bukan repository yang sudah dipublikasikan.

```sh
bench version
bench --site TEST_SITE list-apps
bench --site TEST_SITE backup --with-files
bench get-app REPOSITORY_URL
bench --site TEST_SITE install-app project_billing
bench --site TEST_SITE migrate
bench build --app project_billing
bench restart
```

Untuk repository private, gunakan akses Git milik operator (misalnya SSH key di luar repo). Jangan menaruh token/password di source atau URL remote yang dibagikan.

## Deployment container

Masukkan app ke proses build image/deployment yang persisten. Menambah app hanya pada filesystem container yang sementara akan hilang ketika container dibuat ulang. Perintah build/restart mengikuti konfigurasi deployment; langkah Bench di atas bukan pengganti konfigurasi image.

## Konfigurasi awal

1. Siapkan company, customer, akun, pajak, dan barang kontrak melalui ERPNext.
2. Buat item penagihan non-stock yang aktif dan dapat dijual, tanpa deferred revenue/item tax template.
3. Pada Project Billing Settings, pilih item tersebut dan aktifkan fitur.
4. Buat Project Billing Template dengan total porsi 100%, jenis termin dan credit days sesuai kesepakatan.
5. Siapkan Letter Head dan duplikat print format untuk kebutuhan perusahaan. Mapping tanda tangan staf tidak didistribusikan dalam source.
6. Pastikan worker dan scheduler berjalan; uji alur lengkap menggunakan [ACCEPTANCE.md](ACCEPTANCE.md).

Install/migrate memperbarui print format milik app, termasuk SI JSI. **Duplikat dengan nama lain sebelum melakukan perubahan khusus perusahaan** agar tidak tertimpa migrasi berikutnya. Format hasil edit langsung pada site tidak otomatis menjadi bagian dari source app.

## Pengujian

Tes lokal tanpa Frappe:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Tes integrasi harus dijalankan pada disposable test site sesuai petunjuk README. Simpan log dan dokumen bukti di luar repository. Kelulusan tes lokal tidak membuktikan instalasi pada server baru sudah berhasil.

## Distribusi source

Publikasikan hanya folder repository app ini. Dokumen internal, screenshot, PDF, build lama, dan arsip privat disimpan terpisah. Sebelum commit/push, periksa `git status`, daftar file staged, diff, dan scan secret; `.gitignore` tidak menghapus file yang pernah terlanjur masuk commit.

Paket dapat dibangun menggunakan backend Flit dari `pyproject.toml`. Periksa isi wheel dan source distribution sebelum dibagikan. Repository source untuk Bench harus memuat folder app, templates, JavaScript, DocType JSON, dan metadata build.
