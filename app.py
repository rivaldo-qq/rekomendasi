# Import Library
from flask import Flask, render_template, request, jsonify
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import csr_matrix
import csv
from datetime import datetime

# Setup Flask
app = Flask(__name__)

# Load Dataset
df = pd.read_csv('Penjualan warmindo.csv')

# Perbaiki format nama produk (kapitalisasi yang konsisten)
df['nama_produk'] = df['nama_produk'].str.title()

# User-Item Matrix dengan Rating (asumsikan rating default 5 untuk pembelian)
user_item_matrix = df.pivot_table(index='customer_id',
                                columns='nama_produk',
                                values='quantity',
                                aggfunc='sum',
                                fill_value=0)

# Item-Based Collaborative Filtering
sparse_matrix = csr_matrix(user_item_matrix.values)
item_sim = cosine_similarity(sparse_matrix.T)
item_sim_df = pd.DataFrame(item_sim, 
                         index=user_item_matrix.columns, 
                         columns=user_item_matrix.columns)

# Fungsi Rekomendasi dengan Filter Kategori
def rekomendasi_produk(nama_produk, kategori=None, top_n=6):
    if nama_produk not in item_sim_df.columns:
        return []
    
    # Dapatkan kategori produk yang dipilih
    produk_kategori = df[df['nama_produk'] == nama_produk]['jenis_produk'].iloc[0]
    
    # Hitung similarity scores
    similar_scores = item_sim_df[nama_produk].sort_values(ascending=False)
    
    if kategori:
        # Filter berdasarkan kategori yang dipilih
        produk_kategori_sama = df[df['jenis_produk'] == kategori]['nama_produk'].unique()
        similar_scores = similar_scores[similar_scores.index.isin(produk_kategori_sama)]
    
    rekomendasi = similar_scores.iloc[1:top_n+1]
    return list(rekomendasi.index)

def rekomendasi_produk_by_kategori(kategori, df, top_n=5):
    # Filter data berdasarkan kategori
    df_kat = df[df['jenis_produk'] == kategori]
    # Hitung total penjualan per produk
    populer = df_kat.groupby('nama_produk')['quantity'].sum().sort_values(ascending=False)
    total = populer.sum()
    # Buat list tuple (nama_produk, persentase_popularitas)
    rekomendasi = [(nama, round((qty/total)*100, 2)) for nama, qty in populer.head(top_n).items()]
    return rekomendasi

# Dictionary untuk menyimpan rating (dalam praktik nyata, gunakan database)
ratings_db = {}

# Halaman Utama
@app.route("/", methods=["GET", "POST"])
def index():
    import pandas as pd
    df = pd.read_csv('Penjualan warmindo.csv')
    rekomendasi = []
    kategori_filter = None
    # Dapatkan daftar kategori unik
    kategori_list = sorted(df['jenis_produk'].unique())
    if request.method == "POST":
        kategori_filter = request.form.get("kategori")
        if kategori_filter:
            rekomendasi = rekomendasi_produk_by_kategori(kategori_filter, df, top_n=6)
    return render_template("index.html", 
                         rekomendasi=rekomendasi, 
                         kategori_list=kategori_list,
                         kategori_terpilih=kategori_filter,
                         ratings=ratings_db)

# API untuk menyimpan rating
@app.route("/rate", methods=["POST"])
def rate_product():
    data = request.get_json()
    product_name = data.get('product')
    rating = data.get('rating')
    
    if product_name and rating:
        if product_name not in ratings_db:
            ratings_db[product_name] = {'total': 0, 'count': 0}
        
        ratings_db[product_name]['total'] += int(rating)
        ratings_db[product_name]['count'] += 1
        
        return jsonify({
            'success': True,
            'average': ratings_db[product_name]['total'] / ratings_db[product_name]['count']
        })
    
    return jsonify({'success': False})

@app.route("/favorit", methods=["POST"])
def favorit():
    menu_favorit = request.form.get("menu_favorit")
    kategori = request.form.get("kategori")
    quantity = request.form.get("quantity", 1)
    try:
        quantity = int(quantity)
        if quantity < 1:
            quantity = 1
    except:
        quantity = 1
    if not menu_favorit or not kategori:
        return "Data tidak lengkap", 400

    # Baca data CSV untuk auto increment id dan invoice_id
    with open('Penjualan warmindo.csv', newline='', encoding='utf-8') as f:
        reader = list(csv.reader(f))
        last_row = reader[-1] if len(reader) > 1 else None
        last_id = int(last_row[0]) if last_row else 0
        last_invoice = int(last_row[1]) if last_row else 0

    new_id = last_id + 1
    new_invoice = last_invoice + 1
    tanggal = datetime.now().strftime('%m/%d/%y')
    customer_id = 9999  # Bisa diganti dengan sistem login/user id jika ada
    # Cari harga_jual dari data df
    harga_row = df[df['nama_produk'] == menu_favorit].iloc[0]
    harga_jual = harga_row['harga_jual']
    jenis_produk = harga_row['jenis_produk']
    kategori_produk = harga_row['kategori_produk'] if 'kategori_produk' in harga_row else 'makanan'
    jenis_pembayaran = 'FAVORIT'
    jenis_pesanan = 'Favorit'
    nilai_penjualan = harga_jual * quantity

    # Tulis ke CSV
    with open('Penjualan warmindo.csv', 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            new_id, new_invoice, tanggal, customer_id, menu_favorit, jenis_produk, kategori_produk, quantity, harga_jual, jenis_pembayaran, jenis_pesanan, nilai_penjualan
        ])
    return "<script>alert('Terima kasih, menu favorit Anda sudah disimpan!');window.location='/'</script>"

@app.route("/about")
def about():
    return render_template("about.html")

# Run App
if __name__ == "__main__":
    app.run(debug=True)
