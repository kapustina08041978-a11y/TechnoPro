PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, login TEXT NOT NULL UNIQUE, full_name TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('client','manager','admin')));
CREATE TABLE IF NOT EXISTS equipment (id INTEGER PRIMARY KEY, category_id INTEGER NOT NULL REFERENCES categories(id), name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', specifications TEXT NOT NULL DEFAULT '', country TEXT NOT NULL, daily_price REAL NOT NULL CHECK(daily_price>=0), stock INTEGER NOT NULL CHECK(stock>=0), image_path TEXT);
CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), start_date TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('active','cancelled','completed')) DEFAULT 'active', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS booking_items (id INTEGER PRIMARY KEY, booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE, equipment_id INTEGER NOT NULL REFERENCES equipment(id), quantity INTEGER NOT NULL CHECK(quantity>0), rental_days INTEGER NOT NULL CHECK(rental_days>0), price_per_day REAL NOT NULL CHECK(price_per_day>=0), UNIQUE(booking_id,equipment_id));
INSERT OR IGNORE INTO categories(id,name) VALUES(1,'Электроинструменты'),(2,'Строительное оборудование'),(3,'Измерительные приборы');
INSERT OR IGNORE INTO users(id,login,full_name,role) VALUES(1,'client','Иванов Иван Иванович','client'),(2,'manager','Петров Пётр Сергеевич','manager'),(3,'admin','Сидорова Анна Викторовна','admin');
INSERT OR IGNORE INTO equipment(id,category_id,name,description,specifications,country,daily_price,stock,image_path) VALUES
(1,1,'Перфоратор Bosch GBH 2-26','Для сверления и долбления бетона','Мощность: 830 Вт; энергия удара: 2.7 Дж','Германия',750,5,NULL),
(2,1,'Шуруповёрт Makita DF333','Компактный аккумуляторный шуруповёрт','Напряжение: 12 В; патрон: 10 мм','Япония',450,2,NULL),
(3,2,'Бетономешалка Вихрь БМ-180','Оборудование для приготовления раствора','Объём: 180 л; мощность: 800 Вт','Россия',1900,1,NULL),
(4,3,'Лазерный уровень ADA','Для разметки и строительных работ','Дальность: 20 м; 2 линии','Китай',600,4,NULL),
(5,2,'Виброплита ЗУБР','Для уплотнения грунта и песка','Масса: 60 кг','Россия',2400,0,NULL);
