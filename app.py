import pandas as pd
import gspread
import sqlite3
import string
from datetime import datetime, timedelta
import random
import matplotlib.pyplot as plt
from google.oauth2 import service_account
from datetime import timedelta
import mpld3
from flask import Flask, render_template, request, session, redirect, url_for , flash
from flask_mail import Mail, Message



app = Flask(__name__)

app.secret_key = 'PfdRs1999@A-402'


# Define your Google Sheets credentials JSON file (replace with your own)
credentials_path = 'keys.json'

# Authenticate with Google Sheets using the credentials
credentials = service_account.Credentials.from_service_account_file(credentials_path, scopes=['https://spreadsheets.google.com/feeds'])

# Authenticate with Google Sheets using gspread
gc = gspread.authorize(credentials)

# Your Google Sheets URL
url_acc = "https://docs.google.com/spreadsheets/d/1yQXPZ4zdI8aiIzYXzzuAwDS1V_Zg0fWU6OaqZ_VmwB0/edit#gid=0"
url_targ = "https://docs.google.com/spreadsheets/d/1yQXPZ4zdI8aiIzYXzzuAwDS1V_Zg0fWU6OaqZ_VmwB0/edit#gid=1885515628"

# Open the Google Sheets spreadsheet
worksheet_accounts = gc.open_by_url(url_acc).worksheet("accounts")
worksheet_targets = gc.open_by_url(url_targ).worksheet("targets") 

# connection = sqlite3.connect("dashboard.db")
# cursor = connection.cursor()

# cursor.execute("create TABLE users(employee_number integer primary key, email text, password VARCHAR, name text, reset_token VARCHAR, reset_token_expiry DATETIME)")
# cursor.execute('create TABLE production("TRANSACTION DATE" datetime, "BRANCH", "INTERMEDIARY TYPE", "INTERMEDIARY", "PRODUCT", "PORTFOLIO MIX", "SALES TYPE" num, "SUM INSURED" num, "GROSS PREMIUM" num, "NET BALANCE" num, "RECEIPTS" num, "NEW TM", "MONTH NAME", "DayOfWeek")')

# employee_details = [(10001, 'francis@gmail.com', 'Password123', 'Francis Muruge', '', ''),
#                     (10002, 'zak@gmail.com', 'Password123', 'Zakayo Chemiati','',''),
#                     (10003, 'muriuki@gmail.com', 'Password123', 'Racheal Muriuki', '', ''),
#                     (10004, 'chetekei007@gmail.com', 'Password123', 'Collins Chetekei', '', ''),
#                     (10005, 'beri@gmail.com', 'Password123', 'Beri Allan', '', '')
#                      ]

# cursor.executemany("INSERT OR REPLACE into users values (?,?,?,?, ?, ?)", employee_details)

# for row in cursor.execute("select * from users"):
#     print(row)

# connection.commit()


@app.route("/", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        # Establish connection to the database
        connection = sqlite3.connect("dashboard.db")
        cursor = connection.cursor()

        # Pull the user inputs from the login form
        email = request.form['email']
        password = request.form['password']

        # Create a query to establish a match btwn user_input and what is saved in the database
        query = "SELECT email, password FROM users WHERE email = '"+email+"' AND password = '"+password+"' "
        cursor.execute(query)
        results = cursor.fetchall()  # gets the matches btwn user input and the db

        if len(results) == 0:
            flash('Incorrect credentials. Try again.', 'error')
        else:
            return render_template('form.html')
 
    return render_template('login.html')


@app.route("/upload_file" , methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(url_for('upload_file'))

        file = request.files['file']

        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(url_for('upload_file'))

        if file:
            file_path = 'uploads/' + file.filename
            file.save(file_path)

            # Store the file path in a session variable
            session['uploaded_file_path'] = file_path

            # You might want to read the file into a DataFrame here
            # df = pd.read_csv(file_path)

            return redirect(url_for('home'))

    # Handle the GET request (render the upload form)
    return render_template('form.html')


# Configure Flask-Mail settings
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'chetekeicollins@gmail.com'
app.config['MAIL_PASSWORD'] = 'idtptgybyntrgunr'
app.config['MAIL_DEBUG'] = True

mail = Mail(app) 

# Function to send email with reset token
def send_reset_email(email, reset_token):
    subject = 'Password Reset'
    message = Message(subject=subject, body=body, recipients=[email])
    body = f"Click the following link to reset your password: {url_for('reset_password', token=reset_token, _external=True)}"
    try:
        mail.send(message)
        flash('Email sent successfully. Check your inbox for the confirmation link.', 'success')
    except Exception as e:
        flash(f'Error sending email: {str(e)}', 'error')


#mail.send(message)
    


# Function to generate a random string for the reset token
def generate_reset_token():
    token_length = 20
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(token_length))


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
    if request.method == 'POST':
        email = request.form['email']
        # Establish connection to the database
        connection = sqlite3.connect("dashboard.db")
        cursor = connection.cursor()
        query = "SELECT email FROM users WHERE email = ? "
        cursor.execute(query,(email,))
        user = cursor.fetchone()  # gets the match btwn user input and the db

        if user:
            # Generate a reset token
            reset_token = generate_reset_token()

            # Store the reset token and expiry time in the database
            expiry_time = datetime.now() + timedelta(hours=1)  # Adjust the expiration time as needed
            update_query = "UPDATE users SET reset_token = ?, reset_token_expiry = ? WHERE email = ?"
            cursor.execute(update_query, (reset_token, expiry_time, email))
            connection.commit()

            flash('A password reset link has been sent to your email.', 'info')
            return redirect(url_for('reset_request'))

        else:
            flash('Email not found. Please check your email address.', 'error')
            return redirect(url_for('reset_request'))

    return render_template('reset_request.html')


@app.route("/home")
def home():
    # Retrieve the uploaded file path from the session
    file_path = session.get('uploaded_file_path', None)

    if file_path:
        df,bar_df, image_base64, week_gp, week_receipted, week_credit, month_gp, month_receipted, month_credit, yp, yr, yc = process_uploaded_file(file_path)
        return render_template('home.html', df=df, bar_df=bar_df, image_base64=image_base64, data=df, week_gp=week_gp, week_receipted=week_receipted, week_credit=week_credit, month_gp=month_gp, month_receipted=month_receipted, month_credit=month_credit, yp=yp, yc=yc, yr=yr)
    else:
        return 'No uploaded file found.'


@app.route("/tms")
def tms():
    #Retrieve the uploaded file path from the session
    file_path = session.get('uploaded_file_path', None)

    if file_path:
        if request.method == 'POST':
            selected_manager = request.form.get('manager')

            # Process the selected manager and filter the data
            df, db_df, week_gp, week_receipted, week_credit, month_gp, month_receipted, month_credit = process_uploaded_file(file_path)
            filtered_data = db_df[db_df['INTERMEDIARY'] == selected_manager]
            data_to_render = filtered_data.to_dict(orient='records')

            return render_template('tms.html', data=data_to_render, week_gp=week_gp, week_receipted=week_receipted, week_credit=week_credit, month_gp=month_gp, month_receipted=month_receipted, month_credit=month_credit)

        else:
            # Initial rendering without manager selection
            df, db_df, week_gp, week_receipted, week_credit, month_gp, month_receipted, month_credit = process_uploaded_file(file_path)
            return render_template('tms.html', data=df, week_gp=week_gp, week_receipted=week_receipted, week_credit=week_credit, month_gp=month_gp, month_receipted=month_receipted, month_credit=month_credit)

    else:
        return 'No uploaded file found..'
        



def process_uploaded_file(file_path):
    
    df = pd.read_excel(file_path, header=6)
    df2 = df[["TRANSACTION DATE", "BRANCH", "INTERMEDIARY TYPE", "INTERMEDIARY", "PRODUCT", "PORTFOLIO MIX", "SALES TYPE", "STAMP DUTY", "SUM INSURED", "GROSS PREMIUM", "NET BALANCE", "RECEIPTS", "TM"]].copy()
    df2.loc[df2['INTERMEDIARY'] == 'GWOKA INSURANCE AGENCY', 'BRANCH'] = 'Head Office'
    # Convert the 'Date' column to datetime format
    df2['TRANSACTION DATE'] = pd.to_datetime(df2['TRANSACTION DATE'] , format='%m/%d/%Y')    
    # Replace all occurrences of 2023 with 1/11/2024
    df2['TRANSACTION DATE'] =  df2['TRANSACTION DATE'].mask( df2['TRANSACTION DATE'].dt.year == 2023, '2024-01-11')
    # Extract the day of the week, month and create new columns
    df2['DayOfWeek'] = df2['TRANSACTION DATE'].dt.day_name()
    df2['MONTH NAME'] = df2['TRANSACTION DATE'].dt.strftime('%B')
    df2['MONTH NAME'] = df2['MONTH NAME'].str.upper()

    # Create a pandas Timestamp object
    most_current_date = df2['TRANSACTION DATE'].max()
    current_date = pd.to_datetime(most_current_date)

    timestamp = pd.Timestamp(current_date)
    current_month = timestamp.strftime('%B')
    current_month_name = current_month.upper()       
    

    start_of_week = current_date - timedelta(days=current_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    account_data = worksheet_accounts.get_all_values()
    headers = account_data[0]
    account_data = account_data[1:]
    lastdf = pd.DataFrame(account_data, columns=headers)  # Convert data to a DataFrame
    
    
    jointdf = pd.merge(df2, lastdf, on='INTERMEDIARY', how='left')
    jointdf.loc[jointdf['INTERMEDIARY'].str.contains('REIN', case=False, na=False), 'NEW TM'] = 'REINSURANCE'
    jointdf = jointdf[["TRANSACTION DATE", "BRANCH", "INTERMEDIARY TYPE", "INTERMEDIARY", "PRODUCT", "PORTFOLIO MIX", "SALES TYPE", "SUM INSURED", "GROSS PREMIUM", "NET BALANCE", "RECEIPTS", "NEW TM", "MONTH NAME", "DayOfWeek"]].copy()
    
    newdf = jointdf.dropna(subset='TRANSACTION DATE').copy()
    
    # Push DataFrame to the database
    connection = sqlite3.connect("dashboard.db")
    
    newdf.to_sql('production', connection, if_exists='replace', index=False)

    query = "SELECT * FROM production"
    db_df = pd.read_sql_query(query, connection)
    db_df['TRANSACTION DATE'] = pd.to_datetime(db_df['TRANSACTION DATE'])

    
    bar_df = db_df.groupby('MONTH NAME')['GROSS PREMIUM'].sum().reset_index()

  
    
    # THIS MONTH
    this_month = db_df.loc[db_df['MONTH NAME'] == current_month_name].copy()
    month_prem = this_month['GROSS PREMIUM'].sum()
    month_gp = "Ksh. {:,.0f}".format(month_prem)
   
    month_recpt = this_month['RECEIPTS'].sum() 
    month_receipted = "Ksh. {:,.0f}".format(month_recpt)
 
    month_cr = this_month['NET BALANCE'].sum()
    month_credit = "Ksh. {:,.0f}".format(month_cr)

 
    
    # Get transactions done in the current week
    this_week = db_df.loc[((db_df['TRANSACTION DATE']).dt.date >= start_of_week.date()) & ((db_df['TRANSACTION DATE']).dt.date <= end_of_week.date())].copy()
    week_prem = this_week['GROSS PREMIUM'].sum() 
    week_gp = "Ksh. {:,.0f}".format(week_prem)
  
    week_recpt = this_week['RECEIPTS'].sum()
    week_receipted = "Ksh. {:,.0f}".format(week_recpt)
 
    week_cr = this_week['NET BALANCE'].sum()
    week_credit = "Ksh. {:,.0f}".format(week_cr)


     # MOST RECENT (YESTERDAY)
    most_recent_date = db_df[db_df['TRANSACTION DATE'] == db_df['TRANSACTION DATE'].max()].copy()
    first_recent_date = most_recent_date.iloc[-1] # last date

    friday_df = this_week[this_week['DayOfWeek'] == 'Friday']
    friday = friday_df['GROSS PREMIUM'].sum()
    friday_cancelled = friday_df[friday_df['GROSS PREMIUM'] < 0]['GROSS PREMIUM'].sum()
    friday_receipts = friday_df[friday_df['RECEIPTS'] > 0]['RECEIPTS'].sum()
    friday_credits = friday_df['NET BALANCE'].sum()
    
    saturday_df = this_week.loc[this_week['DayOfWeek'] == 'Saturday']
    saturday = saturday_df['GROSS PREMIUM'].sum()
    saturday_receipts = saturday_df[saturday_df['RECEIPTS'] > 0]['RECEIPTS'].sum()
    saturday_credits = saturday_df['NET BALANCE'].sum()
    saturday_cancelled = saturday_df[saturday_df['GROSS PREMIUM'] < 0]['GROSS PREMIUM'].sum()
    
    sunday_df = this_week.loc[this_week['DayOfWeek'] == 'Sunday']
    sunday = sunday_df['GROSS PREMIUM'].sum()
    sunday_receipts = sunday_df[sunday_df['RECEIPTS'] > 0]['RECEIPTS'].sum()
    sunday_credits = sunday_df['NET BALANCE'].sum()
    sunday_cancelled = sunday_df[sunday_df['GROSS PREMIUM'] < 0]['GROSS PREMIUM'].sum()

   
    if first_recent_date.iloc[0].weekday() == 4:
        yesterday = friday
        yesterday_receipts_total = friday_receipts
        yesterday_credit_total = friday_credits
        cancelled_yesterday = friday_cancelled
        
    elif first_recent_date.iloc[0].weekday() == 5:
        yesterday = (friday + saturday)
        yesterday_receipts_total = friday_receipts + saturday_receipts
        yesterday_credit_total = (friday_credits + saturday_credits)
        cancelled_yesterday = friday_cancelled + saturday_cancelled
        
    elif first_recent_date.iloc[0].weekday() == 6:
        yesterday = (friday + saturday+ sunday)
        yesterday_receipts_total = sunday_receipts
        yesterday_credit_total = (friday_credits + saturday_credits + sunday_credits)
        cancelled_yesterday = friday_cancelled + saturday_cancelled + sunday_cancelled
        
    else:
        
        yesterday = most_recent_date['GROSS PREMIUM'].sum()
        yesterday_receipts_total = most_recent_date.loc[most_recent_date['RECEIPTS'] >= 0, 'RECEIPTS'].sum()
        yesterday_credit_total = most_recent_date.loc[most_recent_date['NET BALANCE'] > 0, 'NET BALANCE'].sum()
        cancelled_yesterday = most_recent_date.loc[most_recent_date['GROSS PREMIUM'] < 0, 'GROSS PREMIUM'].sum()
       

    yp = "Ksh. {:,.0f}".format(yesterday)    
    yr = "Ksh. {:,.0f}".format(yesterday_receipts_total)    
    yc = "Ksh. {:,.0f}".format(yesterday_credit_total)  
    

    unique_manager = db_df['NEW TM'].unique().tolist()

    fig, ax = plt.subplots(figsize=(10,6))
    ax.bar(bar_df['MONTH NAME'], bar_df['GROSS PREMIUM'], color='#00A550',)
    ax.set_xlabel('Month')
    ax.set_title('MONTHLY GROSS UNDERWRITTEN PREMIUM')
   
    # Convert the Matplotlib plot to HTML
    image_base64 = mpld3.fig_to_html(fig)
    
    session['unique_manager'] = unique_manager
    
    df = df2.to_dict(orient='records')
    return df, bar_df, image_base64, week_gp, week_receipted, week_credit, month_gp, month_receipted, month_credit, yp, yc, yr



if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)



    
