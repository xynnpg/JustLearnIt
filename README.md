# JustLearnIt

O platformă de învățare complexă construită cu Flask care oferă o experiență de învățare interactivă și captivantă pentru studenți și educatori.

## Caracteristici

- **Autentificare Utilizator**
  - Sistem securizat de autentificare și înregistrare
  - Verificare prin email
  - Gestionare parole
  - Gestionare sesiuni

- **Module de Învățare**
  - Conținut interactiv de învățare
  - Urmărirea progresului
  - Trimitere și validare răspunsuri
  - Sistem de puncte de experiență (XP)

- **Panou de Administrare**
  - Autentificare securizată pentru administratori
  - Gestionare utilizatori
  - Gestionare conținut
  - Monitorizare sistem

- **Caracteristici Adiționale**
  - Sistem de clasament
  - Gestionare stocare
  - Studio pentru crearea conținutului
  - Personalizare cont
  - Secțiune Despre

## Tehnologii Utilizate

- **Backend**: Flask
- **Bază de Date**: SQLite cu SQLAlchemy ORM
- **Autentificare**: Flask-Login, Flask-Bcrypt
- **Email**: Flask-Mail
- **Formulare**: Flask-WTF, WTForms
- **Migrări Bază de Date**: Flask-Migrate, Alembic
- **Instrumente Adiționale**: 
  - Python-dotenv pentru gestionarea variabilelor de mediu
  - Pillow pentru procesarea imaginilor
  - Gunicorn pentru deployment în producție

## Cerințe Preliminare

- Python 3.x
- pip (manager de pachete Python)
- Mediu virtual (recomandat)

## Instalare

1. Clonați repository-ul:
   ```bash
   git clone [repository-url]
   cd JustLearnIt
   ```

2. Creați și activați un mediu virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Pentru Windows: venv\Scripts\activate
   ```

3. Instalați dependențele:
   ```bash
   pip install -r requirements.txt
   ```

4. Configurați variabilele de mediu:
   Creați un fișier `.env` în directorul rădăcină cu următoarele variabile:
   ```
   SECRET_KEY=cheia_ta_secreta
   MAIL_USERNAME=emailul_tau
   MAIL_PASSWORD=parola_emailului_tau
   MAIL_DEFAULT_SENDER=emailul_tau
   ADMIN_EMAIL=email_administrator
   ```

5. Inițializați baza de date:
   ```bash
   python init_db.py
   ```

## Rularea Aplicației

1. Mod dezvoltare:
   ```bash
   python run.py
   ```

2. Mod producție:
   ```bash
   gunicorn app:app
   ```

Aplicația va fi disponibilă la adresa `http://localhost:5000`

## Structura Proiectului

```
JustLearnIt/
├── AboutPage/         # Componente pagină Despre
├── AccountPage/       # Gestionare cont utilizator
├── AdminPage/         # Panou administrator
├── ChoosePage/        # Interfață de selecție
├── LandingPage/       # Pagină principală
├── LearnPage/         # Module de învățare
├── LoginPage/         # Autentificare
├── RankingPage/       # Clasamente utilizatori
├── StoragePage/       # Gestionare stocare
├── StudioPage/        # Creare conținut
├── static/           # Fișiere statice (CSS, JS, imagini)
├── Templates/        # Șabloane HTML
├── storage/          # Stocare bază de date
├── app.py           # Fișier principal aplicație
├── models.py        # Modele bază de date
├── extensions.py    # Extensii Flask
├── utils.py         # Funcții utilitare
└── requirements.txt # Dependențe proiect
```

## Caracteristici de Securitate

- Gestionare securizată a sesiunilor
- Criptare parole
- Protecție CSRF
- Setări securizate pentru cookie-uri
- Rotație credențiale administrator
- Notificări de autentificare

## Contribuție

1. Fork repository-ul
2. Creați o branch pentru funcționalitate
3. Commit modificările
4. Push la branch
5. Creați un Pull Request

## Licență

[Adăugați informațiile despre licență aici]

## Suport

Pentru asistență, vă rugăm să contactați [informațiile de contact] 