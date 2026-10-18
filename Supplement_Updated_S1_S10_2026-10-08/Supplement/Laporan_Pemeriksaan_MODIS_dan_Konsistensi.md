# Pemeriksaan bias pengamatan MODIS dan konsistensi analisis

Tanggal pemeriksaan: 5 Oktober 2026. Pemeriksaan selesai untuk data yang tersedia. Hubungan hujan–hari deteksi bertahan pada beberapa subset pengamatan; pengaruh awan belum dapat diukur karena mask pengamatan tidak tersedia. Manuskrip, tabel utama, figur, dan skrip dalam paket ini memakai satu versi analisis yang sama.

## Hasil yang direproduksi

| Komponen | Hasil |
| --- | --- |
| Panel hujan historis | 773 sel; 1.694.416 grid-hari; 3.059 hari deteksi type = 0; 2020–2025 penuh |
| Model utama | Logistik bersyarat; OR 10,50; interval sekitar 95% 6,78–16,27; 0–10 versus >100 mm hujan tujuh hari |
| Informasi model | 1.420 strata informatif; 43.283 pengamatan; 420 klaster sel dan 70 klaster tahun-bulan |
| Luas terbakar 2023 | 4,41% di dalam ID 6; 1,29% di luar ID 6; rasio 3,41 |
| Sensitivitas QA luas terbakar | Rasio 3,29 dan 3,39; angka 3,60 dari pemeriksaan batas terdahulu dipertahankan sebagai hasil arsip |
| Sensor Oktober 2023 | 171,2 µg/m³; tetap puncak pada jaringan tetap dan setelah KR_06 dikeluarkan |

## Pemeriksaan pengamatan MODIS

CSV mentah diperiksa untuk rentang tanggal, atribut type, dan duplikasi. Tidak ditemukan duplikasi pada kunci lokasi–tanggal–waktu–satelit. Perbandingan tahunan memakai 1 Januari–26 September; pemodelan hujan memakai seluruh kalender 2020–2025. Data 2026 tetap deskriptif dan sementara.

| Subset | OR 0–10 versus >100 mm | Interval sekitar 95% |
| --- | --- | --- |
| Primary full year | 10.50 | 6.78–16.27 |
| High confidence, vegetation type | 13.98 | 6.83–28.62 |
| Terra only | 15.37 | 8.11–29.13 |
| Aqua only | 8.99 | 5.44–14.86 |
| Daytime only | 8.94 | 5.59–14.31 |
| Nighttime only | 22.71 | 9.23–55.87 |
| Scan and track ≤1.5 km | 9.55 | 6.24–14.62 |

Semua interval untuk kontras ini tetap di atas satu. Arah pola konsisten pada subset tersebut; besar efeknya berbeda, terutama pada deteksi malam. Perbedaan ini tidak digunakan untuk menyimpulkan efek biologis siang–malam atau kesetaraan peluang observasi.

Proporsi Terra dari seluruh deteksi berubah dari 22,1% pada 2023 menjadi 41,2% pada 2026. Proporsi ini bersyarat pada deteksi yang tercatat, bukan proporsi seluruh kesempatan pengamatan. Oleh karena itu, kenaikan hitungan 2026 tidak dijadikan bukti tersendiri tentang kenaikan keparahan kebakaran.

## Apa yang belum dapat dikoreksi

FIRMS CSV berisi deteksi positif dan tidak memuat piksel berawan, non-api, unknown, ataupun swath yang hilang. Hari tanpa deteksi berarti **tidak ada deteksi tercatat**, bukan konfirmasi bahwa hari tersebut bebas api pada langit cerah. Dokumentasi NASA menjelaskan bahwa awan dan asap tebal dapat menghalangi deteksi. Pemeriksaan satelit, confidence, dan ukuran piksel tidak menggantikan mask ini.

Untuk koreksi kuantitatif diperlukan MOD14/MYD14 beserta mask api dan geolokasinya, atau data ketersediaan pengamatan yang setara. Produk harian MOD14A1/MYD14A1 dapat mendukung penyaringan ketersediaan harian, tetapi merupakan komposit dan tidak menyediakan jumlah seluruh overpass individual. Produk ini **belum dimasukkan** dalam analisis sekarang; tidak ada nilai koreksi awan yang diasumsikan. Makna ilmiah hasil tetap dibatasi pada asosiasi hujan dengan deteksi yang diamati.

## Penyelarasan versi

- Abstract, Methods, Results, Table 2, Figure 3, dan graphical abstract menggunakan model logistik bersyarat utama serta periode historis penuh.
- IRR 0,316 dari model Poisson lama dipertahankan hanya pada Table S9, dengan interval yang dihitung ulang secara konsisten.
- Figure 2 membandingkan 2023 dengan 2026 pada jendela kalender yang sama. Peta Figure 1 mengikuti desain revisi pengguna.
- Table 3 dan Figure 4 dibuat dari hasil raster dan sensor yang sama; tabel pendukung menggunakan nomor S1–S9.
- Setiap figur/tabel dihubungkan ke skrip dan input melalui Artifact_Index.csv.
- Kesimpulan dan acknowledgement MEXT pengguna dipertahankan. Atribusi asap dan prediksi paparan dinyatakan sebagai agenda penelitian selanjutnya.

## Cakupan reproduksi pada pemeriksaan ini

Klasifikasi MODIS, panel hujan, model logistik dan Poisson, serta raster Burn Date/QA dihitung ulang dari input yang tersedia. Tabel sensor/CAMS disusun dari keluaran pemeriksaan data mentah yang telah selesai sebelumnya pada 5 Oktober; keluaran tersebut dipertahankan dengan bukti checksum dan audit. Pemeriksaan ini tidak mengolah ulang angin atau analisis populasi, yang tidak menjadi hasil utama versi terfokus ini.

Kelengkapan ekstrak ID 6 telah diverifikasi terhadap kueri, tetapi produsen/tahun/skala pemetaan asli masih belum dinyatakan dalam metadata. Pemetaan field ekspor sensor ke kanal fisik dan batas waktu rata-rata hariannya juga belum seluruhnya eksplisit. Pemeriksaan sensitivitas tidak dianggap menyelesaikan informasi sumber tersebut.

## Sumber dokumentasi pemeriksaan

- NASA FIRMS, The Impact of Cloud on Active Fire Detections (2024): https://wiki.earthdata.nasa.gov/spaces/FIRMS/blog/2024/08/07/382276882/The+Impact+of+Cloud+on+Active+Fire+Detections
- NASA LAADS, MODIS fire-mask specification: https://ladsweb.modaps.eosdis.nasa.gov/filespec/MODIS/6/MOD14
- MODIS active-fire product guides: https://modis-fire.umd.edu/guides.html
- Graham et al. (2024), data: https://doi.org/10.5281/zenodo.13767528; article: https://doi.org/10.1029/2024GH001125
- CAMS EAC4: https://doi.org/10.24381/d58bbf47

Paket ini menyelaraskan hasil yang dipertahankan dalam manuskrip. Berkas arsip dan analisis eksploratif lama di luar paket tidak diubah; gunakan Legacy_to_Current_Version_Map.csv untuk membedakan versi.
