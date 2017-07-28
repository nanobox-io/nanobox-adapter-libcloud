from nanobox_libcloud import app


# Start development server if this script is executed directly
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
