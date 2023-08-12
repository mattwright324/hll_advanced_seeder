# Using a modified 'example 2' class of colors
# https://www.geeksforgeeks.org/print-colors-python-terminal/
#
# Example usage
# import colors as c
# print(f'{c.red}Hello world{c.reset}')

reset = '\033[0m'
bold = '\033[01m'
disable = '\033[02m'
underline = '\033[04m'
reverse = '\033[07m'
strikethrough = '\033[09m'
invisible = '\033[08m'

black = '\033[30m'
red = '\033[31m'
green = '\033[32m'
orange = '\033[33m'
blue = '\033[34m'
purple = '\033[35m'
cyan = '\033[36m'
lightgrey = '\033[37m'
darkgrey = '\033[90m'
lightred = '\033[91m'
lightgreen = '\033[92m'
yellow = '\033[93m'
lightblue = '\033[94m'
pink = '\033[95m'
lightcyan = '\033[96m'


def demo():
    print(f'{black}black{reset}')
    print(f'{red}red{reset}')
    print(f'{green}green{reset}')
    print(f'{orange}orange{reset}')
    print(f'{blue}blue{reset}')
    print(f'{purple}purple{reset}')
    print(f'{cyan}cyan{reset}')
    print(f'{lightgrey}lightgrey{reset}')
    print(f'{darkgrey}darkgrey{reset}')
    print(f'{lightred}lightred{reset}')
    print(f'{lightgreen}lightgreen{reset}')
    print(f'{yellow}yellow{reset}')
    print(f'{lightblue}lightblue{reset}')
    print(f'{pink}pink{reset}')
    print(f'{lightcyan}lightcyan{reset}')

    print(f'{bold}bold{reset}')
    print(f'{disable}disable{reset}')
    print(f'{underline}underline{reset}')
    print(f'{reverse}reverse{reset}')
    print(f'{strikethrough}strikethrough{reset}')
    print(f'{invisible}invisible{reset}')