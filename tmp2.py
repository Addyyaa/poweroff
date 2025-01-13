class person():
    name = ''
    sex = ''
    age = 0
    region = 'China'

    def __init__(self, name, sex, age):
        self.name = name
        self.sex = sex
        self.age = age

    def tell_personal_info(self):
        print(f'我叫：{self.name} 是一个 {self.sex}生，今年我 {self.age}岁', {self.region})

    def set_region(self):
        self.region = 'USA'

    def action(self, eat, watch):
        print(f'我喜欢吃{eat}，我也喜欢看{watch}')


niye = person('倪晔', '男', 18)
niye.tell_personal_info()
shenfeng = person('沈峰', '男', 22)
shenfeng.tell_personal_info()
shenfeng.action('电影', '饭')
