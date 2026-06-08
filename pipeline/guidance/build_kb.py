import os
# pyrefly: ignore [missing-import]
import chromadb

client = chromadb.HttpClient(host=os.getenv("CHROMA_HOST", "localhost"), port=8000)

# Delete existing collection to reset embeddings and schema
try:
    client.delete_collection("manasik_knowledge")
    print("Deleted old manasik_knowledge collection")
except Exception:
    pass

# Create collection with Chroma's default embedding function (ONNX all-MiniLM-L6-v2)
collection = client.get_or_create_collection("manasik_knowledge")

SEED_DOCS = [
    # Rukun & Wajib Umrah
    {
        "text": "Rukun Umrah ada 5 perkara yang harus dipenuhi agar ibadah Umrah sah dan tidak bisa diganti dengan denda (dam): 1) Niat Ihram dari Miqat, 2) Tawaf mengelilingi Ka'bah sebanyak 7 kali putaran, 3) Sa'i antara Bukit Shafa dan Marwah sebanyak 7 kali perjalanan, 4) Tahallul atau memotong/mencukur sebagian rambut kepala, dan 5) Tertib melaksanakan semua rukun secara berurutan.",
        "phase": "ritual", "topic": "rukun_umrah", "lang": "id"
    },
    {
        "text": "Wajib Umrah ada 2 perkara yang jika dilanggar ibadahnya tetap sah namun wajib membayar denda (dam) atau bertaubat: 1) Berihram (niat) dari Miqat makani (batas tempat yang ditentukan), dan 2) Menjauhi larangan-larangan ihram selama beribadah.",
        "phase": "ritual", "topic": "wajib_umrah", "lang": "id"
    },
    # Ihram / Niat
    {
        "text": "Ihram adalah niat memulai ibadah Umrah atau Haji dengan memakai pakaian ihram di Miqat yang telah ditentukan. Lafal niat Umrah adalah: 'Labbaikallahumma 'Umratan' (Aku penuhi panggilan-Mu ya Allah untuk berumrah). Setelah berniat, jamaah wajib menjauhi larangan-larangan ihram.",
        "phase": "ritual", "topic": "ihram", "lang": "id"
    },
    {
        "text": "Larangan Ihram bagi laki-laki meliputi: memakai pakaian biasa yang berjahit, memakai sepatu yang menutupi mata kaki, dan memakai penutup kepala. Bagi perempuan larangan meliputi: menutup wajah (cadar) dan menutup kedua telapak tangan (sarung tangan).",
        "phase": "ritual", "topic": "larangan_ihram_gender", "lang": "id"
    },
    {
        "text": "Larangan Ihram bagi laki-laki dan perempuan meliputi: memakai wewangian (pada tubuh, pakaian, rambut), memotong rambut atau bulu badan, memotong kuku, memburu binatang liar, melakukan akad nikah, serta melakukan hubungan suami istri (jima') atau bermesraan.",
        "phase": "ritual", "topic": "larangan_ihram_umum", "lang": "id"
    },
    # Tawaf
    {
        "text": "Tawaf adalah mengelilingi Ka'bah sebanyak 7 putaran secara berlawanan arah jarum jam (Ka'bah berada di sebelah kiri jamaah), dimulai dari Hajar Aswad dan diakhiri di Hajar Aswad pula. Syarat sah Tawaf: suci dari hadas kecil/besar, menutup aurat, dan dilakukan di dalam Masjidil Haram.",
        "phase": "ritual", "topic": "tawaf", "lang": "id"
    },
    # Sa'i
    {
        "text": "Sa'i adalah berjalan kaki sebanyak 7 kali perjalanan antara Bukit Shafa dan Bukit Marwah. Perjalanan dimulai dari Bukit Shafa menuju Bukit Marwah (dihitung 1 kali), lalu kembali dari Marwah ke Shafa (dihitung 2 kali), hingga berakhir di Bukit Marwah pada hitungan ke-7. Sunnah sa'i bagi laki-laki adalah berlari-lari kecil di antara lampu hijau.",
        "phase": "ritual", "topic": "sai", "lang": "id"
    },
    # Tahallul
    {
        "text": "Tahallul adalah mencukur gundul atau memotong sebagian rambut kepala setelah menyelesaikan ibadah Sa'i. Bagi laki-laki disunnahkan mencukur gundul (halq) atau memotong rambut secara merata. Bagi perempuan, cukup memotong ujung rambut sepanjang satu ruas jari (minimal 3 helai rambut). Tahallul menandakan selesainya ibadah Umrah dan terbebasnya jamaah dari seluruh larangan ihram.",
        "phase": "ritual", "topic": "tahallul", "lang": "id"
    },
    # Rukun & Wajib Haji
    {
        "text": "Rukun Haji ada 6 perkara yang wajib dikerjakan dan tidak sah haji jika ditinggalkan: 1) Ihram (niat haji), 2) Wukuf di Arafah pada 9 Dzulhijjah, 3) Tawaf Ifadhah, 4) Sa'i antara Shafa dan Marwah, 5) Tahallul (mencukur/memotong rambut), dan 6) Tertib.",
        "phase": "ritual", "topic": "rukun_haji", "lang": "id"
    },
    {
        "text": "Wajib Haji ada 6 perkara yang jika ditinggalkan hajinya tetap sah tetapi wajib membayar denda (dam): 1) Niat ihram dari Miqat, 2) Mabit (bermalam) di Muzdalifah, 3) Mabit di Mina pada hari-hari Tasyrik (11, 12, 13 Dzulhijjah), 4) Melontar Jumrah (Jumrah Ula, Wusta, dan Aqabah), 5) Menjauhkan diri dari larangan ihram, dan 6) Melaksanakan Tawaf Wada' sebelum meninggalkan kota Makkah.",
        "phase": "ritual", "topic": "wajib_haji", "lang": "id"
    },
    # Wukuf & Mabit & Jumrah
    {
        "text": "Wukuf di Arafah dilaksanakan pada tanggal 9 Dzulhijjah mulai dari masuknya waktu Dzuhur (tergelincirnya matahari) sampai fajar tanggal 10 Dzulhijjah. Wukuf merupakan puncak ibadah haji di mana jamaah memperbanyak dzikir, istighfar, dan doa.",
        "phase": "ritual", "topic": "wukuf", "lang": "id"
    },
    {
        "text": "Mabit di Muzdalifah dilakukan setelah bertolak dari Arafah pada malam tanggal 10 Dzulhijjah. Jamaah berada di Muzdalifah minimal hingga lewat tengah malam untuk berdoa, berdzikir, dan mengumpulkan batu kerikil untuk melontar jumrah.",
        "phase": "ritual", "topic": "mabit_muzdalifah", "lang": "id"
    },
    {
        "text": "Mabit di Mina dan melontar jumrah dilakukan pada hari Nahr (10 Dzulhijjah) dan hari-hari Tasyrik (11, 12, 13 Dzulhijjah). Jamaah bermalam di Mina dan melontar tiga tiang jumrah (Ula, Wusta, Aqabah) menggunakan kerikil sebanyak 7 buah per tiang secara berurutan.",
        "phase": "ritual", "topic": "mabit_mina_jumrah", "lang": "id"
    },
    # Tawaf Wada
    {
        "text": "Tawaf Wada' adalah tawaf perpisahan yang wajib dilakukan oleh setiap jamaah haji sebelum meninggalkan kota Makkah untuk kembali ke tanah air atau ke Madinah. Tawaf ini tidak diikuti dengan sa'i dan melambangkan penghormatan terakhir kepada Baitullah.",
        "phase": "return", "topic": "tawaf_wada", "lang": "id"
    },
    # Predeparture Documents
    {
        "text": "Dokumen wajib yang harus disiapkan sebelum keberangkatan Haji atau Umrah meliputi: 1) Paspor asli dengan masa berlaku minimal 6 bulan sebelum tanggal keberangkatan, 2) Visa Haji/Umrah yang diterbitkan resmi oleh Pemerintah Arab Saudi, 3) Kartu Kuning bukti Vaksinasi Meningitis, dan 4) Surat Mahram (jika diperlukan untuk jamaah wanita tertentu).",
        "phase": "predeparture", "topic": "documents", "lang": "id"
    },
    # English equivalents for RAG search robustness
    {
        "text": "Umrah consists of 5 essential pillars (Rukun): 1) Ihram (intention from Miqat), 2) Tawaf (circumambulating Kaaba 7 times), 3) Sa'i (walking 7 times between Shafa and Marwah), 4) Tahallul (shaving/cutting hair), and 5) Tertib (performing in order).",
        "phase": "ritual", "topic": "rukun_umrah", "lang": "en"
    },
    {
        "text": "Hajj consists of 6 pillars (Rukun): 1) Ihram (intention for Hajj), 2) Wuquf at Arafah (9th Dzulhijjah), 3) Tawaf Ifadhah, 4) Sa'i, 5) Tahallul, and 6) Tertib.",
        "phase": "ritual", "topic": "rukun_haji", "lang": "en"
    }
]

collection.add(
    documents=[d["text"] for d in SEED_DOCS],
    metadatas=[{"phase": d["phase"], "topic": d["topic"], "lang": d["lang"]} for d in SEED_DOCS],
    ids=[f"doc_{i}" for i in range(len(SEED_DOCS))],
)
print(f"Ingested {len(SEED_DOCS)} documents into manasik_knowledge")
