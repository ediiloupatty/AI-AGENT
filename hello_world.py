# hello_world.py
#
# Program sederhana untuk menyapa user.
# Menunjukkan input/output dasar di Python.

print("👋 Selamat datang di program sederhana!")

# Minta input nama dari user
nama = input("Siapa nama kamu? ").strip()

# Periksa apakah nama kosong
if nama:
    print(f"Halo, {nama}! Senang bertemu denganmu. 🌟")
else:
    print("Halo, teman baru! 😊")

print("\nProgram selesai. Terima kasih sudah mencoba!")
