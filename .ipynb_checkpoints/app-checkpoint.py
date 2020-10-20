from flask import Flask, render_template, session, request, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import datetime
import hashlib
import urllib
import numpy as np
import cv2

from base64 import b64encode
from detection import upload_to_gcs
from detection import generate_download_signed_url_v4
from detection import get_similar_products_uri
from detection import query_product

app = Flask(__name__)
app.secret_key = 'keye'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://mkhoa:NTMK261194@dng@35.221.181.94:3306/project' #veritabanını bağlıyoruz
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
project_id = 'abstract-veld-289612'
location = 'asia-east1'
product_set_id = 'PAIR-Filter'
bucket_name = 'ftmle'
product_category= 'homegoods-v2'
color = [(255,0,0), 
         (0,255,0), 
         (0,0, 255), 
         (135, 170, 170), 
         (135, 100, 125), 
         (135, 100, 190), 
         (0, 255, 255), 
         (255, 255, 255),
        (255, 0, 255),
        (255, 255, 255)]

#SQLAlchemy yapısı ve classlar kullanarak veritabanı oluşturma işlemlerini yapılıyor.
class Kullanicilar(db.Model):
    __tablename__ = "Kullanicilar"
    id = db.Column(db.Integer, primary_key=True, autoincrement = True, unique=True)
    kullanici_adi = db.Column(db.Text,nullable=False)
    email = db.Column(db.Text, unique=True)
    sifre = db.Column(db.Text,nullable=False)
    yetki = db.Column(db.Integer, nullable=False)

class ProductHeader(db.Model): # Urunler
    __tablename__ = "ProductHeader"
    id = db.Column(db.Integer, primary_key=True, autoincrement = True, unique=True)
    website = db.Column(db.String(100),nullable=True)
    category = db.Column(db.String(255),nullable=True)
    category_url = db.Column(db.Text,nullable=True)
    image = db.Column(db.Text,nullable=True)
    product = db.Column(db.Text,nullable=False)
    price = db.Column(db.String(255),nullable=True)
    url = db.Column(db.Text,nullable=True)

class Sepet(db.Model):
    __tablename__ = "Sepet"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    urun_id = db.Column(db.Integer, db.ForeignKey('Kullanicilar.id'))
    adet = db.Column(db.Integer, nullable=False)

class Siparis(db.Model):
    __tablename__ = "Siparis"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    kullanici_id = db.Column(db.Integer, db.ForeignKey('Kullanicilar.id'))
    urun_id = db.Column(db.Integer, db.ForeignKey('Urunler.urunid'))
    tarih = db.Column(db.Text, nullable=False)
    adet = db.Column(db.Integer, nullable=False)

#Giriş-Çıkış, adminlik ve giriş yapan kullanıcı bilgileri için değişkenleri global olarak tanımlanıyor.
yetki=False
girisyapildi=False
kullanici=''

def search_product(bucket_name, blob_name):
    serving_url = generate_download_signed_url_v4(bucket_name, blob_name)
    res = get_similar_products_uri(project_id, location, product_set_id, product_category,
        image_uri=serving_url, filter='')
    return res, serving_url

def url_to_image(url):
    # download the image, convert it to a NumPy array, and then read
    # it into OpenCV format
    resp = urllib.request.urlopen(url)
    image = np.asarray(bytearray(resp.read()), dtype="uint8")
    image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    # return the image
    return image

def draw_bounding(res, img_url):
    img = url_to_image(img_url)
    font = cv2.FONT_HERSHEY_SIMPLEX
    fontScale = 2
    fontColor = (0,255,255)
    lineType = 5
    string = ''
    for i in range(len(res)):
        w = img.shape[1]
        h = img.shape[0]
        x1 = int(res[i].bounding_poly.normalized_vertices[0].x * w)
        y1 = int(res[i].bounding_poly.normalized_vertices[0].y * h)
        x2 = int(res[i].bounding_poly.normalized_vertices[2].x * w)
        y2 = int(res[i].bounding_poly.normalized_vertices[2].y * h)
        result = cv2.rectangle(img,(x1,y1), (x2,y2), color[i], thickness=5)
        result = cv2.putText(result,str(i), (x1, y1), font, fontScale, fontColor, lineType)  
        result = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
    return result
    
@app.route('/')
def index():
    header=ProductHeader.query.limit(120).all() #Ürünleri veritabanından çekiyoruz
    #index sayfasına değişkenleri ürünleri ve index htmli gönderiyoruz
    return render_template('index.html', Header=header) 

@app.route('/shopthelook')
def shopthelook():
  return render_template('shopthelook.html')

@app.route('/shopthelook', methods = ['POST'])
def upload_file():
    uploaded_file = request.files['file']
    content = uploaded_file.read()
    if uploaded_file.filename != '':
        fname = str(datetime.datetime.now().date()) + '_' + str(datetime.datetime.now().time()).replace(':', '.') + '-' + uploaded_file.filename
        blob_name = 'Images/Uploads/' + fname
        response = upload_to_gcs(content, bucket_name, blob_name)
    
    res, serving_url = search_product(bucket_name, blob_name)
    
    result = []
    for i in range(len(res)):    
        for j in range(len(res[i].results)):
            d = {}
            d['object'] = i
            d['idx'] = int(res[i].results[j].product.name.split('/', -1)[-1])
            d['score'] = res[i].results[j].score
            result.append(d)
    
    result = pd.DataFrame(result)  
    query = pd.DataFrame(result['idx'].apply(query_product).tolist(), columns=['idx', 'Website', 'Name', 'Image', 'URL', 'Category'])
    df = result.merge(query)
    df = df.drop_duplicates('idx')
    df = df[df['score'] > 0.5].sort_values(by='Category')
    
    result_img = b64encode(draw_bounding(res, serving_url)).decode("utf-8")
    
    return render_template('shopthelook.html', product_search=response, tables=[df.to_html(classes='data')], titles=df.columns.values,
                          results = df, bounding_box=result_img, s_url=serving_url)

@app.route('/uyeol', methods = ['POST', 'GET'])
def uyeol():
    if request.method == 'POST':
        #html'deki formlar yardımıyla üye bilgilerini alıyoruz.
        ad = request.form['ad']
        email = request.form['email']
        sifre = request.form['sifre']
        #üyenin şifresini 256 bit hash ile şifreliyoruz
        hashli=hashlib.sha256(sifre.encode("utf8")).hexdigest()
        #kullanıcının bilgilerini veritabanına gönderiyoruz
        user = Kullanicilar(kullanici_adi=ad, sifre=hashli, email=email, yetki=0)
        db.session.add(user) 
        db.session.commit()
        return redirect(url_for('girisyap'))
    else:
        return render_template('signup.html')

@app.route('/girisyap', methods=['GET', 'POST'])
def girisyap():
    if request.method == 'POST':
        #html ile giriş yapmak isteyen kullanıcının bilgilerini alıyoruz
        email = request.form['email']
        sifre = request.form['sifre']
        hashli=hashlib.sha256(sifre.encode("utf8")).hexdigest()
        
        #kullanıcı giriş yaptığında yeni sepet oluşturuyoruz
        sepet = Sepet.query.all()
        for S in sepet:
            S.adet = 0
        db.session.commit()


        global kullanici
        kullanici = email

        # kullanıcının admin olup olmadığının bu if else ile kontrol ediyoruz.(yetki 1 admin -- yetki 0 admin değil)
        if Kullanicilar.query.filter_by(email=email, sifre=hashli, yetki=1).first():
            global yetki
            global girisyapildi        
            yetki = True
            girisyapildi = True
            
            return redirect(url_for('index'))
        else:
            data = Kullanicilar.query.filter_by(email=email, sifre=hashli).first()
            if data is not None:
                girisyapildi = True
                yetki = False
                             
                return redirect(url_for('index'))
            else:
                return render_template('login.html')
    return render_template('login.html')

@app.route('/cikisyap')
def cikis():
    #kullanıcı çıkış yapacağı zaman globalde tanımladığımız değişkenleri sıfırlıyoruz
    global yetki
    global girisyapildi
    global kullanici
    kullanici=""
    yetki = False
    girisyapildi = False
    
    #çıkış yapılırken sepeti veritabanından temizliyoruz.
    sepet = Sepet.query.all()
    for sepet in sepet:
        sepet.adet = 0
    db.session.commit()

    return redirect(url_for('index'))

@app.route('/urunekle', methods = ['POST', 'GET'])
def urunekle():
    if request.method == 'POST':   
        #html yardımıyla eklenecek ürünün bilgilerini alıyoruz
        urunadi = request.form['urunadi']
        fiyat = request.form['fiyat']
        resim = request.form['resim']
        stok = request.form['stok']
        #ürünü veritabanına gönderiyoruz.
        urunumuz = Urunler(urunadi=urunadi, fiyat=fiyat, resim=resim, stok=stok)
        db.session.add(urunumuz)  
        db.session.commit()

        #aynı ürünü sepet tablosunada gönderiyoruz (sepet ekleme işlemleri için)
        sepet = Sepet(urun_id = urunumuz.urunid, adet = 0)
        db.session.add(sepet)
        db.session.commit()

        return redirect(url_for('index'))
    else:
        return render_template('urunekle.html', yetki = yetki)

@app.route('/urunsil', methods = ['POST', 'GET'])
def urunsil():
    if request.method == 'POST':
      #silinecek ürünün adını html ile alıyoruz ve veri tabanından siliyoruz.
      sili = Urunler.query.filter_by(urunadi=request.form['aranan']).first()
      db.session.delete(sili)
      db.session.commit()
      return redirect(url_for('index'))
    return render_template('urunsil.html', yetki = yetki)

@app.route('/urunduzenle', methods = ['POST', 'GET'])
def urunduzenle():
    if request.method == 'POST':
      #html'deki form ile düzenleyeceğimiz ürünün önce adını sonrada yeni bilgilerini alıyoruz ve veritabanını güncelliyoruz
      dzn = Urunler.query.filter_by(urunadi=request.form['aranan1']).first()
      dzn.urunadi = request.form['urunadi']
      dzn.fiyat = request.form['fiyat']
      dzn.resim = request.form['resim']
      dzn.stok = request.form['stok']
      db.session.add(dzn)
      db.session.commit()
      return redirect(url_for('index'))
    else:        
      return render_template('urunduzenle.html', yetki = yetki)

@app.route('/sepet')
def sepet():
  #veritabanında sepet tablosundaki adet sayısı 0 dan büyük olanları çekiyoruz dolayısıyla sepetteki ürünleri sayısı ile birlikte öğrenmiş oluyoruz
  #daha sonrada sepet sayfasına bu ürünleri göndererek html yardımı ile listeliyoruz
  sepet = Sepet.query.filter((Sepet.adet > 0)).all()
  urunler = Urunler.query.all()
  return render_template('cart.html', sepet = sepet, urunler = urunler, girisyapildi = girisyapildi)

@app.route('/sepeteekle/<urun_id>/<sepetten>', methods = ['POST', 'GET'])
def sepeteekle(urun_id,sepetten):
  if request.method == 'POST':
    #sepete ürün eklerken gelen urunid ile ürünü bulup sepet tablosundaki adetini bir arttırarak sepete eklemiş veya sayısını arttırmış oluyoruz.
    if sepetten == 'True':
      urun = Urunler.query.filter_by(urunid = urun_id).first()
      sepet = Sepet.query.filter_by(urun_id = urun_id).first()
      if urun.stok > sepet.adet:
        sepet.adet += 1
        db.session.commit()
      return redirect(url_for('sepet'))
    else:
       urun = Urunler.query.filter_by(urunid = urun_id).first()
       sepet = Sepet.query.filter_by(urun_id = urun_id).first()
       if urun.stok > sepet.adet:
           sepet.adet += 1
           db.session.commit()
    return redirect(url_for('index'))
  else:
    return redirect(url_for('index'))

@app.route('/sepettensil/<urun_id>', methods = ['POST', 'GET'])
def sepettensil(urun_id):
  #gelen ürün id nin sepetteki adetini 1 azaltıyoruz adet 0 olunca sepetten ürün silinmiş oluyor
  sepet = Sepet.query.filter_by(urun_id = urun_id).first()
  sepet.adet -= 1
  db.session.commit()
  return redirect(url_for('sepet'))

@app.route('/sepetitemizle')
def sepetitemizle():
    #sepetteki tüm ürünlerin adetini 0 yaparak sepeti temizliyoruz.
    sepet = Sepet.query.all()
    for S in sepet:
        S.adet = 0
    db.session.commit()
    return redirect(url_for('sepet'))

@app.route('/satinal', methods = ['POST', 'GET'])
def satinal():
  #ürünü hangi kullanıcının aldığı bilgisini sepeti ve bugünki tarihi sipariş tablosuna gönderiyoruz
  #bu bilgiler sipariş tablosunda tutuluyor
  global kullanici
  user = Kullanicilar.query.filter_by(kullanici_adi=kullanici).first()
  sepet = Sepet.query.filter((Sepet.adet > 0)).all()
  urun = Urunler.query.all()
  bugun = datetime.datetime.now()
  for s in sepet:
      for u in urun:
        if s.urun_id == u.urunid:
          siparis = Siparis(kullanici_id=u.urunid, urun_id=u.urunid, tarih = bugun.strftime("%Y-%m-%d %H:%M"), adet=s.adet)
          u.stok -= s.adet #sipariş tamamlandığında ürünün stoktaki sayısı 1 azaltılıyor
          db.session.add(siparis)
          db.session.add(u)
          db.session.commit()
# en son sipariş tamamlandığı için kullanıcının sepeti temizleniyor
  sepet = Sepet.query.all()
  for s in sepet:
    s.adet = 0
  db.session.commit()
  return redirect(url_for('index'))

if __name__ == '__main__':
  app.run(debug=True, host='0.0.0.0', port=8085)

 