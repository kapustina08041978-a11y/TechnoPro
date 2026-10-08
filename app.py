"""ТехноПро: учебная система проката. Запуск: python app.py"""
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'technopro.db'
BLUE, LIGHT, RED = '#176c99', '#f2f8fc', '#ffe1e1'

@contextmanager
def connect():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def initialize():
    with connect() as conn:
        conn.executescript((ROOT / 'database.sql').read_text(encoding='utf-8'))

def get_items():
    with connect() as conn:
        return conn.execute('''SELECT e.*,c.name AS category,
            EXISTS(SELECT 1 FROM booking_items bi JOIN bookings b ON bi.booking_id=b.id
            WHERE bi.equipment_id=e.id AND b.status!='cancelled'
            AND b.start_date>=date('now','start of month','-1 month')
            AND b.start_date<date('now','start of month')) AS used_last_month
            FROM equipment e JOIN categories c ON c.id=e.category_id''').fetchall()

def price(item):
    return round(item['daily_price'] * (1 if item['used_last_month'] else 0.85), 2)

class TechnoPro(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('ТехноПро — аренда оборудования')
        self.geometry('1060x740')
        self.configure(bg=LIGHT)
        self.user = None
        self.basket = {}
        self.search = tk.StringVar()
        self.category = tk.StringVar(value='Все категории')
        self.sort = tk.StringVar(value='Без сортировки')
        self.page = None
        self.placeholder = tk.PhotoImage(file=str(ROOT / 'picture.png'))
        self.login_page()

    def frame(self, title, back=None):
        if self.page:
            self.page.destroy()
        self.page = ttk.Frame(self, padding=15)
        self.page.pack(fill='both', expand=True)
        bar = ttk.Frame(self.page)
        bar.pack(fill='x', pady=(0,15))
        if back:
            ttk.Button(bar,text='← Назад',command=back).pack(side='left',padx=(0,10))
        ttk.Label(bar,text='ТехноПро — '+title,font=('Arial',19,'bold')).pack(side='left')
        if self.user:
            ttk.Label(bar,text=self.user['full_name']).pack(side='right')
        return self.page

    def login_page(self):
        self.user = None
        parent = self.frame('Вход')
        ttk.Label(parent,text='Выберите логин (без пароля)').pack(anchor='w')
        with connect() as conn:
            users = conn.execute('SELECT * FROM users ORDER BY id').fetchall()
        labels = [f"{u['login']} — {u['full_name']} ({u['role']})" for u in users]
        selected = ttk.Combobox(parent,values=labels,state='readonly',width=70)
        selected.pack(anchor='w',pady=12)
        if labels:
            selected.current(0)
        def enter():
            if selected.current()<0:
                messagebox.showwarning('Внимание','Выберите пользователя')
                return
            self.user = dict(users[selected.current()])
            self.catalog()
        ttk.Button(parent,text='Войти',command=enter).pack(anchor='w')

    def catalog(self):
        parent = self.frame('Каталог')
        line = ttk.Frame(parent)
        line.pack(fill='x',pady=5)
        ttk.Label(line,text='Поиск:').pack(side='left')
        ttk.Entry(line,textvariable=self.search,width=24).pack(side='left',padx=5)
        with connect() as conn:
            categories = [r['name'] for r in conn.execute('SELECT name FROM categories ORDER BY name')]
        ttk.Combobox(line,textvariable=self.category,values=['Все категории']+categories,state='readonly',width=22).pack(side='left',padx=5)
        ttk.Combobox(line,textvariable=self.sort,values=['Без сортировки','Цена: по возрастанию','Цена: по убыванию'],state='readonly',width=23).pack(side='left',padx=5)
        ttk.Button(line,text=f'Корзина ({sum(q for q,d in self.basket.values())})',command=self.basket_page).pack(side='right',padx=3)
        ttk.Button(line,text='Бронирования',command=self.bookings_page).pack(side='right',padx=3)
        ttk.Button(line,text='Выход',command=self.login_page).pack(side='right',padx=3)
        outer = ttk.Frame(parent)
        outer.pack(fill='both',expand=True,pady=10)
        canvas = tk.Canvas(outer,bg=LIGHT,highlightthickness=0)
        scroll = ttk.Scrollbar(outer,orient='vertical',command=canvas.yview)
        list_frame = tk.Frame(canvas,bg=LIGHT)
        window = canvas.create_window((0,0),window=list_frame,anchor='nw')
        list_frame.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=e.width))
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side='left',fill='both',expand=True)
        scroll.pack(side='right',fill='y')
        def update(*args):
            for child in list_frame.winfo_children():
                child.destroy()
            items = [i for i in get_items() if (self.category.get()=='Все категории' or i['category']==self.category.get()) and self.search.get().lower() in (i['name']+' '+i['description']).lower()]
            if self.sort.get()=='Цена: по возрастанию':
                items.sort(key=price)
            elif self.sort.get()=='Цена: по убыванию':
                items.sort(key=price,reverse=True)
            for i in items:
                bg = RED if i['stock']<=1 else '#ffffff'
                card = tk.Frame(list_frame,bg=bg,bd=1,relief='solid',padx=12,pady=10)
                card.pack(fill='x',pady=4)
                tk.Label(card,image=self.placeholder,bg=bg,width=110,height=80).pack(side='left',padx=(0,12))
                status = 'Достаточно' if i['stock']>3 else 'Мало'
                text = f"{i['name']}  |  {i['category']}  |  {i['country']}\n{price(i):.2f} ₽/день  |  На складе: {i['stock']} ({status})" + ('  |  Скидка 15%' if not i['used_last_month'] else '')
                tk.Label(card,text=text,bg=bg,justify='left',anchor='w',font=('Arial',11)).pack(side='left',fill='x',expand=True)
                ttk.Button(card,text='Подробнее',command=lambda item=i:self.detail(item['id'])).pack(side='right')
            if not items:
                ttk.Label(list_frame,text='Ничего не найдено').pack()
        for var in (self.search,self.category,self.sort):
            var.trace_add('write',update)
        update()

    def detail(self,item_id):
        item = next(i for i in get_items() if i['id']==item_id)
        page = self.frame('Карточка инструмента',self.catalog)
        tk.Label(page,image=self.placeholder,bg=LIGHT).pack(anchor='w',pady=6)
        for line in (item['name'],f"Категория: {item['category']}",f"Страна: {item['country']}",f"Описание: {item['description']}",f"Характеристики: {item['specifications']}",f"Доступно: {item['stock']}",f"Цена: {price(item):.2f} ₽/день",'Изображение: picture.png (заглушка)'):
            ttk.Label(page,text=line,font=('Arial',12),wraplength=950).pack(anchor='w',pady=5)
        if self.user['role']!='client':
            ttk.Label(page,text='Бронирование доступно при входе клиента').pack(anchor='w')
            return
        count = tk.IntVar(value=1)
        days = tk.IntVar(value=1)
        ttk.Label(page,text='Количество:').pack(anchor='w')
        tk.Spinbox(page,from_=1,to=max(1,item['stock']),textvariable=count,width=8).pack(anchor='w')
        ttk.Label(page,text='Срок аренды (дни):').pack(anchor='w')
        tk.Spinbox(page,from_=1,to=365,textvariable=days,width=8).pack(anchor='w')
        def add():
            try:
                q,d=int(count.get()),int(days.get())
                prev=self.basket.get(item_id,(0,d))[0]
                if q<1 or d<1 or q+prev>item['stock']:
                    raise ValueError('Некорректное количество или недостаточный остаток')
                if item_id in self.basket and self.basket[item_id][1]!=d:
                    raise ValueError('У этой позиции уже выбран другой срок аренды')
                self.basket[item_id]=(q+prev,d)
                messagebox.showinfo('Успешно','Инструмент добавлен в список бронирования')
                self.catalog()
            except (ValueError,tk.TclError) as ex:
                messagebox.showwarning('Ошибка',str(ex))
        ttk.Button(page,text='Добавить в бронирование',command=add).pack(anchor='w',pady=15)

    def basket_page(self):
        page=self.frame('Оформление бронирования',self.catalog)
        if not self.basket:
            ttk.Label(page,text='Список пуст').pack()
            return
        items={i['id']:i for i in get_items()}
        total=0
        for equipment_id,(q,d) in self.basket.items():
            item=items[equipment_id]
            subtotal=price(item)*q*d
            total+=subtotal
            row=ttk.Frame(page)
            row.pack(fill='x',pady=5)
            ttk.Label(row,text=f"{item['name']} — {q} шт. × {d} дн. × {price(item):.2f} ₽ = {subtotal:.2f} ₽").pack(side='left')
            ttk.Button(row,text='Удалить',command=lambda k=equipment_id:self.remove_basket(k)).pack(side='right')
        ttk.Label(page,text=f'Итого: {total:.2f} ₽',font=('Arial',14,'bold')).pack(anchor='w',pady=12)
        start=tk.StringVar(value=date.today().isoformat())
        ttk.Label(page,text='Дата начала (ГГГГ-ММ-ДД):').pack(anchor='w')
        ttk.Entry(page,textvariable=start).pack(anchor='w',pady=5)
        def confirm():
            try:
                chosen=date.fromisoformat(start.get())
                if chosen<date.today():
                    raise ValueError('Дата начала не может быть в прошлом')
                with connect() as conn:
                    for item_id,(quantity,days) in self.basket.items():
                        current=conn.execute('SELECT stock FROM equipment WHERE id=?',(item_id,)).fetchone()
                        if current is None or current['stock']<quantity:
                            raise ValueError('Недостаточно оборудования на складе')
                    cursor=conn.execute('INSERT INTO bookings(user_id,start_date) VALUES(?,?)',(self.user['id'],start.get()))
                    booking_id=cursor.lastrowid
                    for item_id,(quantity,days) in self.basket.items():
                        p=price(items[item_id])
                        conn.execute('INSERT INTO booking_items(booking_id,equipment_id,quantity,rental_days,price_per_day) VALUES(?,?,?,?,?)',(booking_id,item_id,quantity,days,p))
                        conn.execute('UPDATE equipment SET stock=stock-? WHERE id=?',(quantity,item_id))
                self.basket.clear()
                messagebox.showinfo('Успешно',f'Бронирование №{booking_id} оформлено')
                self.catalog()
            except (ValueError,sqlite3.Error) as ex:
                messagebox.showerror('Ошибка оформления',str(ex))
        ttk.Button(page,text='Подтвердить бронирование',command=confirm).pack(anchor='w',pady=8)
        ttk.Button(page,text='Отменить оформление',command=self.clear_basket).pack(anchor='w')

    def remove_basket(self,key):
        self.basket.pop(key,None)
        self.basket_page()

    def clear_basket(self):
        self.basket.clear()
        self.catalog()

    def bookings_page(self):
        page=self.frame('Бронирования',self.catalog)
        columns=('id','start_date','client','status','total')
        tree=ttk.Treeview(page,columns=columns,show='headings',height=14)
        for key,name in zip(columns,('№','Начало','Клиент','Статус','Стоимость')):
            tree.heading(key,text=name)
            tree.column(key,width=150)
        tree.pack(fill='both',expand=True)
        with connect() as conn:
            query='''SELECT b.id,b.start_date,u.full_name AS client,b.status,
                COALESCE(SUM(bi.quantity*bi.rental_days*bi.price_per_day),0) AS total
                FROM bookings b JOIN users u ON u.id=b.user_id
                LEFT JOIN booking_items bi ON bi.booking_id=b.id'''
            params=()
            if self.user['role']=='client':
                query+=' WHERE b.user_id=?'
                params=(self.user['id'],)
            query+=' GROUP BY b.id ORDER BY b.id DESC'
            for r in conn.execute(query,params):
                tree.insert('', 'end',values=(r['id'],r['start_date'],r['client'],r['status'],f"{r['total']:.2f} ₽"))
        def chosen():
            selection=tree.selection()
            if not selection:
                messagebox.showwarning('Внимание','Выберите бронирование')
                return None
            return int(tree.item(selection[0],'values')[0])
        buttons=ttk.Frame(page)
        buttons.pack(fill='x',pady=10)
        ttk.Button(buttons,text='Состав заказа',command=lambda:self.booking_detail(chosen()) if chosen() is not None else None).pack(side='left',padx=4)
        if self.user['role'] in ('manager','admin'):
            ttk.Button(buttons,text='Добавить заказ',command=self.admin_add).pack(side='left',padx=4)
            ttk.Button(buttons,text='Удалить заказ',command=lambda:self.delete_booking(chosen()) if chosen() is not None else None).pack(side='left',padx=4)
        if self.user['role']=='admin':
            ttk.Button(buttons,text='Изменить заказ',command=lambda:self.edit_booking(chosen()) if chosen() is not None else None).pack(side='left',padx=4)

    def booking_detail(self,booking_id):
        if booking_id is None:
            return
        with connect() as conn:
            rows=conn.execute('''SELECT e.name,bi.quantity,bi.rental_days,bi.price_per_day
                FROM booking_items bi JOIN equipment e ON e.id=bi.equipment_id WHERE booking_id=?''',(booking_id,)).fetchall()
        lines=[f"{r['name']}: {r['quantity']} шт., {r['rental_days']} дн., итог {r['quantity']*r['rental_days']*r['price_per_day']:.2f} ₽" for r in rows]
        messagebox.showinfo('Состав заказа №'+str(booking_id),'\n'.join(lines) or 'Нет позиций')

    def delete_booking(self,booking_id):
        if booking_id is None or not messagebox.askyesno('Подтверждение','Удалить заказ №'+str(booking_id)+'?'):
            return
        with connect() as conn:
            status=conn.execute('SELECT status FROM bookings WHERE id=?',(booking_id,)).fetchone()
            if not status:
                return
            if status['status']=='active':
                self.restore_stock(conn,booking_id)
            conn.execute('DELETE FROM bookings WHERE id=?',(booking_id,))
        self.bookings_page()

    @staticmethod
    def restore_stock(conn,booking_id):
        for item in conn.execute('SELECT equipment_id,quantity FROM booking_items WHERE booking_id=?',(booking_id,)).fetchall():
            conn.execute('UPDATE equipment SET stock=stock+? WHERE id=?',(item['quantity'],item['equipment_id']))

    def admin_add(self):
        page=self.frame('Добавление заказа',self.bookings_page)
        with connect() as conn:
            clients=conn.execute("SELECT * FROM users WHERE role='client'").fetchall()
            items=conn.execute('SELECT * FROM equipment').fetchall()
        if not clients or not items:
            ttk.Label(page,text='Нет клиентов или оборудования').pack()
            return
        clients_box=ttk.Combobox(page,values=[f"{u['id']} — {u['full_name']}" for u in clients],state='readonly',width=48)
        clients_box.current(0)
        clients_box.pack(anchor='w',pady=6)
        products=ttk.Combobox(page,values=[f"{i['id']} — {i['name']}" for i in items],state='readonly',width=48)
        products.current(0)
        products.pack(anchor='w',pady=6)
        qty=tk.IntVar(value=1)
        days=tk.IntVar(value=1)
        start=tk.StringVar(value=date.today().isoformat())
        for label,value in [('Количество',qty),('Дней',days)]:
            ttk.Label(page,text=label).pack(anchor='w')
            ttk.Entry(page,textvariable=value).pack(anchor='w')
        ttk.Label(page,text='Начало аренды (ГГГГ-ММ-ДД)').pack(anchor='w')
        ttk.Entry(page,textvariable=start).pack(anchor='w')
        def save():
            try:
                date.fromisoformat(start.get())
                q,d=int(qty.get()),int(days.get())
                if q<1 or d<1:
                    raise ValueError('Количество и дни должны быть положительными')
                u=clients[clients_box.current()]
                item=items[products.current()]
                with connect() as conn:
                    changed=conn.execute('UPDATE equipment SET stock=stock-? WHERE id=? AND stock>=?',(q,item['id'],q))
                    if changed.rowcount==0:
                        raise ValueError('Недостаточно оборудования')
                    booking=conn.execute('INSERT INTO bookings(user_id,start_date) VALUES(?,?)',(u['id'],start.get())).lastrowid
                    p=price(next(i for i in get_items() if i['id']==item['id']))
                    conn.execute('INSERT INTO booking_items(booking_id,equipment_id,quantity,rental_days,price_per_day) VALUES(?,?,?,?,?)',(booking,item['id'],q,d,p))
                messagebox.showinfo('Успешно','Заказ добавлен')
                self.bookings_page()
            except (ValueError,sqlite3.Error) as ex:
                messagebox.showerror('Ошибка',str(ex))
        ttk.Button(page,text='Сохранить заказ',command=save).pack(anchor='w',pady=10)

    def edit_booking(self,booking_id):
        if booking_id is None:
            return
        page=self.frame('Редактирование заказа №'+str(booking_id),self.bookings_page)
        with connect() as conn:
            booking=conn.execute('SELECT * FROM bookings WHERE id=?',(booking_id,)).fetchone()
            rows=conn.execute('''SELECT bi.*,e.name FROM booking_items bi JOIN equipment e ON e.id=bi.equipment_id WHERE booking_id=?''',(booking_id,)).fetchall()
        if not booking:
            return
        start=tk.StringVar(value=booking['start_date'])
        status=tk.StringVar(value=booking['status'])
        ttk.Label(page,text='Дата начала (ГГГГ-ММ-ДД)').pack(anchor='w')
        ttk.Entry(page,textvariable=start).pack(anchor='w')
        ttk.Label(page,text='Статус').pack(anchor='w')
        ttk.Combobox(page,textvariable=status,values=['active','cancelled','completed'],state='readonly').pack(anchor='w')
        def save():
            try:
                date.fromisoformat(start.get())
                with connect() as conn:
                    old=conn.execute('SELECT status FROM bookings WHERE id=?',(booking_id,)).fetchone()['status']
                    if old!='cancelled' and status.get()=='cancelled':
                        self.restore_stock(conn,booking_id)
                    elif old=='cancelled' and status.get()!='cancelled':
                        for item in conn.execute('SELECT equipment_id,quantity FROM booking_items WHERE booking_id=?',(booking_id,)).fetchall():
                            updated=conn.execute('UPDATE equipment SET stock=stock-? WHERE id=? AND stock>=?',(item['quantity'],item['equipment_id'],item['quantity']))
                            if not updated.rowcount:
                                raise ValueError('Недостаточно оборудования для восстановления заказа')
                    conn.execute('UPDATE bookings SET start_date=?,status=? WHERE id=?',(start.get(),status.get(),booking_id))
                messagebox.showinfo('Успешно','Заказ изменён')
                self.bookings_page()
            except (ValueError,sqlite3.Error) as ex:
                messagebox.showerror('Ошибка',str(ex))
        ttk.Button(page,text='Сохранить изменения',command=save).pack(anchor='w',pady=8)
        ttk.Label(page,text='Позиции заказа (можно удалить отдельно)').pack(anchor='w',pady=8)
        for item in rows:
            row=ttk.Frame(page)
            row.pack(fill='x',pady=4)
            ttk.Label(row,text=f"{item['name']} — {item['quantity']} шт., {item['rental_days']} дн.").pack(side='left')
            ttk.Button(row,text='Удалить позицию',command=lambda x=item['id']:self.delete_item(booking_id,x)).pack(side='right')
        ttk.Button(page,text='Добавить позицию',command=lambda:self.add_booking_item(booking_id)).pack(anchor='w',pady=8)

    def delete_item(self,booking_id,item_id):
        with connect() as conn:
            item=conn.execute('SELECT * FROM booking_items WHERE id=? AND booking_id=?',(item_id,booking_id)).fetchone()
            status=conn.execute('SELECT status FROM bookings WHERE id=?',(booking_id,)).fetchone()['status']
            if item:
                if status!='cancelled':
                    conn.execute('UPDATE equipment SET stock=stock+? WHERE id=?',(item['quantity'],item['equipment_id']))
                conn.execute('DELETE FROM booking_items WHERE id=?',(item_id,))
        self.edit_booking(booking_id)

    def add_booking_item(self,booking_id):
        page=self.frame('Добавить позицию в заказ',lambda:self.edit_booking(booking_id))
        with connect() as conn:
            items=conn.execute('SELECT * FROM equipment ORDER BY id').fetchall()
        product=ttk.Combobox(page,values=[f"{i['id']} — {i['name']}" for i in items],state='readonly',width=50)
        product.pack(anchor='w',pady=8)
        if items:
            product.current(0)
        qty=tk.IntVar(value=1)
        days=tk.IntVar(value=1)
        for name,var in [('Количество',qty),('Дней',days)]:
            ttk.Label(page,text=name).pack(anchor='w')
            ttk.Entry(page,textvariable=var).pack(anchor='w')
        def save():
            try:
                item=items[product.current()]
                q,d=int(qty.get()),int(days.get())
                if q<1 or d<1:
                    raise ValueError('Количество и дни должны быть положительными')
                with connect() as conn:
                    status=conn.execute('SELECT status FROM bookings WHERE id=?',(booking_id,)).fetchone()['status']
                    if status!='cancelled':
                        result=conn.execute('UPDATE equipment SET stock=stock-? WHERE id=? AND stock>=?',(q,item['id'],q))
                        if not result.rowcount:
                            raise ValueError('Недостаточно оборудования')
                    p=price(next(i for i in get_items() if i['id']==item['id']))
                    conn.execute('''INSERT INTO booking_items(booking_id,equipment_id,quantity,rental_days,price_per_day)
                        VALUES(?,?,?,?,?) ON CONFLICT(booking_id,equipment_id) DO UPDATE SET quantity=quantity+excluded.quantity,rental_days=excluded.rental_days''',(booking_id,item['id'],q,d,p))
                self.edit_booking(booking_id)
            except (ValueError,sqlite3.Error) as ex:
                messagebox.showerror('Ошибка',str(ex))
        ttk.Button(page,text='Добавить',command=save).pack(anchor='w',pady=10)

if __name__=='__main__':
    initialize()
    TechnoPro().mainloop()
