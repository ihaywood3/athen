from distutils.core import setup
setup(name='athen',
      version='1.0',
      description='client for ATHEN',
      author='Ian Haywood',
      author_email='ian@haywood.id.au',
      package_dir = {'athen': 'client','athen.lib':'lib'},
      packages= ['athen.lib','athen'],
      license='GPL3',
      url='http://athen.email'
      )
