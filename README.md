# Проект - личный кабинет партнера Adesk
Использованный стек: **Django**,  **PostgreSQL**, **bootstrap**, **nginx & gunicorn**, **docker-compose**, **ansible**


### Постановка задачи
Adesk — это поставщик ПО, продаваемого по подписке. Партнёр —
лицо, имеющее базу клиентов, потенциально заинтересованных в
использовании основного сервиса Adesk. Партнёр имеет возможность
подписывать своих клиентов на ПО Adesk и получать за это доход в размере
партнёрской комиссии. Необходимо:

1. Разработать формы регистрации и авторизации партнёра в партнёрской
программе.
2. Разработать личный кабинет партнёра с формой оформления подписок и другое.
3. Разработать интерфейс django admin для управления учетными записями.
4. Развернуть сервис в виде контейнеров Docker с помощью docker-compose.
5. Написать ansible-playbook для развертывания на сервере.

[Подробнее о задании](https://docs.google.com/document/d/1shrwljSlEMJJt53IOk3PkahRgWYm_7H1WTHU7AoXCrw/edit?usp=sharing) [docs.google]

Информация о тарифах, их квотах, ценах и пользователях Adesk подтягивается по api и динамически генирирует django форму. Сигнал об оформлении подписки также уходит по api к Adesk.

#### Спроектированная база данных
<img src= "https://user-images.githubusercontent.com/59840795/183479197-b900f998-6c08-4f2b-8fd4-c14dbfd9e30c.png"  width="500"/>


## Конечный результат
<img src= "https://user-images.githubusercontent.com/59840795/183481562-f5e7df19-6577-4408-8cab-ee7fa7f99e90.png"  width="700"/>
<hr>

<img src= "https://user-images.githubusercontent.com/59840795/183481936-f3eb2780-2cb4-4936-84d9-26fe4986812b.png"  width="700"/>
<hr>
<img src= "https://user-images.githubusercontent.com/59840795/183481959-481f4461-4b41-4f91-bace-a2a5df760d7b.png"  width="700"/>
<hr>
<img src= "https://user-images.githubusercontent.com/59840795/183482104-3b8774f9-f170-447c-9117-9a5e5efe315e.png"  width="700"/>

<hr>
<img src= "https://user-images.githubusercontent.com/59840795/183483121-a090eb2e-e63a-4511-a507-4dd537ad8c5f.png"  width="700"/>
<hr>
<img src= "https://user-images.githubusercontent.com/59840795/183483138-21cef87f-e4a8-4085-87a6-1b985b181239.png"  width="700"/>
