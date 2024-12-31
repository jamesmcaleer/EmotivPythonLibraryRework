from cortex import Cortex
from colorama import Fore, Back, Style

class Demo:
    def __init__(self, client_id, client_secret, debug):
        self.client_id = client_id
        self.client_secret = client_secret
        self.debug = debug
        self.token = None

        self.cortex = Cortex(self.client_id, self.client_secret, self.debug)

    def authorize_user(self):
        self.current_username = input(f'Enter your {Fore.MAGENTA}EMOTIV ID{Style.RESET_ALL}: ')
    
        result = self.cortex.await_response( api_call=self.cortex.get_user_login )

        
        if self.current_username == result[0]['username']:
            print(f'{Fore.GREEN}Correct{Style.RESET_ALL} {Fore.MAGENTA}EMOTIV ID{Style.RESET_ALL}')
            print(f'Last Login: {Fore.CYAN}{result[0]['lastLoginTime']}{Style.RESET_ALL}')
        else:
            print(f'{Fore.RED}Incorrect{Style.RESET_ALL} {Fore.MAGENTA}EMOTIV ID{Style.RESET_ALL}')
            return
        
        
        result = self.cortex.await_response( api_call=self.cortex.request_access, client_id=self.client_id, client_secret=self.client_secret )
        if result['accessGranted'] == False:
            print(f'{Fore.RED}please approve this application in EMOTIV launcher{Style.RESET_ALL}')
            return

        if not self.token:
            result = self.cortex.await_response( api_call=self.cortex.authorize, client_id=self.client_id, client_secret=self.client_secret )
            self.token = result['cortexToken']
        else: # generate a new one for good measure
            result = self.cortex.await_response( api_call=self.cortex.generate_new_token, cortex_token=self.token, client_id=self.client_id, client_secret=self.client_secret )
            self.token = result['cortexToken']

    def display_user_info(self):
        result = self.cortex.await_response( api_call=self.cortex.get_user_information, cortex_token=self.token )
        self.user_info = result
        print(f"{Fore.GREEN}user information{Style.RESET_ALL} ---")
        print(f"\t{Fore.CYAN}username{Style.RESET_ALL}: {result['username']}")
        print(f"\t{Fore.CYAN}first name{Style.RESET_ALL}: {result['firstName']}")
        print(f"\t{Fore.CYAN}last name{Style.RESET_ALL}: {result['lastName']}")
        print(f"\t{Fore.CYAN}license agreement{Style.RESET_ALL}: {result['licenseAgreement']['accepted']}")


    def show_subjects(self):
        result = self.cortex.await_response( api_call=self.cortex.query_subjects, cortex_token=self.token, query={"sex":"M"}, order_by=[{"subjectName": "DESC"}] )
        self.all_subjects = result
        try:
            print(result['code'])
            print(result['message'])
            return
        except KeyError:
            pass

        print(f"{result['count']} {Fore.YELLOW}subject(s){Style.RESET_ALL} found:")
        for i in range(result['count']):
            print(f"{Fore.MAGENTA}{i}{Style.RESET_ALL}: {result['subjects'][i]['subjectName']}")

        self.subject_index = int(input(f"{Fore.GREEN}Select{Style.RESET_ALL} a {Fore.YELLOW}subject{Style.RESET_ALL} by its {Fore.MAGENTA}index{Style.RESET_ALL}. ({Fore.MAGENTA}-1{Style.RESET_ALL} to create a {Fore.GREEN}new{Style.RESET_ALL} {Fore.YELLOW}subject{Style.RESET_ALL}): "))
        self.current_subject = None

    def create_subject(self):
        create_subject_params = {
            'api_call': self.cortex.create_subject,
            'cortex_token': self.token
        }
        print(f'{Fore.CYAN}Enter the following information{Style.RESET_ALL}:')
        self.subject_name = input(f'subject name {Fore.RED}(required){Style.RESET_ALL}: ')
        if self.subject_name:
            create_subject_params['subject_name'] = self.subject_name
        
        print(f'The following are {Fore.RED}NOT{Style.RESET_ALL} required, press {Fore.BLUE}enter{Style.RESET_ALL} to leave blank')
        date_of_birth = input(f'date of birth {Fore.CYAN}(YYYY-MM-DD){Style.RESET_ALL}: ')
        if date_of_birth:
            create_subject_params['dateOfBirth'] = date_of_birth

        sex = input(f'sex {Fore.CYAN}(M, F, or U){Style.RESET_ALL}: ')
        if sex:
            create_subject_params['sex'] = sex

        country_code = input(f'country code {Fore.CYAN}(ex. US, GB, FI){Style.RESET_ALL}: ')
        if country_code:
            create_subject_params['countryCode'] = country_code

        state = input('state: ')
        if state:
            create_subject_params['state'] = state

        city = input('city: ')
        if city:
            create_subject_params['city'] = city

        result = self.cortex.await_response( **create_subject_params )
        print(f'{Fore.YELLOW}Subject{Style.RESET_ALL} {Fore.GREEN}successfully created!{Style.RESET_ALL}')
        self.current_subject = result
    
    def select_subject(self):
        self.current_subject = self.all_subjects['subjects'][self.subject_index]

    def display_subject_info(self):
        print(f'{Fore.YELLOW}subject{Style.RESET_ALL} information ---')
        for key in self.current_subject:
            print(f"{Fore.CYAN}{key}{Style.RESET_ALL}: {self.current_subject[key]}")

    def show_records(self):
        result = self.cortex.await_response( api_call=self.cortex.query_records, cortex_token=self.token, query={"keyword":self.current_subject['subjectName']}, order_by=[{"startDatetime": "DESC"}] )
        self.all_records = result
        try:
            print(result['code'])
            print(result['message'])
            return
        except KeyError:
            pass
    
        print(f"{result['count']} {Fore.YELLOW}record(s){Style.RESET_ALL} found for {Fore.MAGENTA}{self.current_subject['subjectName']}{Style.RESET_ALL}:")
        for i in range(result['count']):
            print(f"{Fore.MAGENTA}{i}{Style.RESET_ALL}: {result['records'][i]['title']}")

        self.record_index = int(input(f"{Fore.GREEN}Select{Style.RESET_ALL} a {Fore.YELLOW}record{Style.RESET_ALL} by its {Fore.MAGENTA}index{Style.RESET_ALL}. ({Fore.MAGENTA}-1{Style.RESET_ALL} to create a {Fore.GREEN}new{Style.RESET_ALL} {Fore.YELLOW}record{Style.RESET_ALL}): "))
        self.current_record = None

    def create_record(self):
        self.find_headset()

        self.select_streams()

        create_record_params = {
            'api_call': self.cortex.create_record,
            'session_id': self.session_id,
            'cortex_token': self.token
        }
        print(f'{Fore.CYAN}Enter the following information{Style.RESET_ALL}:')
        title = input(f'title {Fore.RED}(required){Style.RESET_ALL}: ')
        if title:
            create_record_params['title'] = title
        
        print(f'The following are {Fore.RED}NOT{Style.RESET_ALL} required, press {Fore.BLUE}enter{Style.RESET_ALL} to leave blank')
        subject_name = input(f'subject name: ')
        if subject_name:
            create_record_params['subjectName'] = subject_name
        else:
            subject_name = self.subject_name
        
        description = input(f'description: ')
        if description:
            create_record_params['description'] = description

        #result = cortex.await_response( api_call=cortex.update_session, cortex_token=token, session_id=session_id, status="active")

        #result = cortex.await_response( **create_record_params )
        #print(f'{Fore.YELLOW}Record{Style.RESET_ALL} {Fore.GREEN}successfully created!{Style.RESET_ALL}')
        #current_record = result

    def display_record_info(self):
        self.record_ids = [self.all_records['records'][self.record_index]['uuid']] 
        result = self.cortex.await_response( api_call=self.cortex.get_record_infos, cortex_token=self.token, record_ids=self.record_ids) # get record with markers
        self.current_record = result[0]

        print(f'{Fore.YELLOW}record{Style.RESET_ALL} information ---')
    
        for key in self.current_record:
            print(f"{Fore.CYAN}{key}{Style.RESET_ALL}: {self.current_record[key]}")

    def find_headset(self):
        result = self.cortex.await_response( api_call=self.cortex.control_device, command="refresh")
        print(f'{Fore.MAGENTA}{result}{Style.RESET_ALL}')
        warning = self.cortex.await_warning() # wait for warning 142 - headset scan finished
        print(warning)
        result = self.cortex.await_response( api_call=self.cortex.query_headsets )
        print(f'{Fore.GREEN}headset(s) found!{Style.RESET_ALL}')
        for hs in result:
            print(f'- {hs['id']}')
        self.headset = result[0]
        self.headset_id = self.headset['id']
        result = self.cortex.await_response( api_call=self.cortex.control_device, command="connect", headset_id=self.headset_id)
        print(f'{Fore.GREEN}{result}{Style.RESET_ALL}')
        warning = self.cortex.await_warning() # wait for warning 100, 101, 102, or 113 - connection was succsessful
        print(f'{Fore.GREEN}{warning}{Style.RESET_ALL}')

        result = self.cortex.await_response( api_call=self.cortex.create_session, cortex_token=self.token, headset_id=self.headset_id, status="open")
        try:
            print(result['code'])
            print(result['message'])
            return
        except KeyError:
            pass

        #print(result)
        self.session_id = result['id']

    def select_streams(self):
        stream_dic = {
            0: "mot",
            1: "dev",
            2: "eq",
            3: "power",
            4: "met", 
            5: "fac",
            6: "sys"
        }
        print(f'{Fore.GREEN}available{Style.RESET_ALL} streams ---')
        for key in stream_dic:
            print(f"{Fore.MAGENTA}{key}{Style.RESET_ALL}: {stream_dic[key]}")

        self.streams = []
        stream_index = 0
        while stream_index >= 0 and stream_index <= 6:
            stream_index = int(input(f"pick a {Fore.YELLOW}stream{Style.RESET_ALL} from the available {Fore.YELLOW}streams{Style.RESET_ALL} ({Fore.MAGENTA}-1{Style.RESET_ALL} to finish picking): "))
            if stream_index not in self.streams:
                self.streams.append(stream_index)
                print(f'stream {Fore.GREEN}added!{Style.RESET_ALL}')
            else:
                print(f'stream {Fore.RED}already entered{Style.RESET_ALL}')

        for i in range(len(self.streams)):
            self.streams[i] = stream_dic[i]
        
        print(f'{Fore.YELLOW}streams{Style.RESET_ALL}: {self.streams}')
        result = self.cortex.await_response( api_call=self.cortex.subscribe, cortex_token=self.token, session_id=self.session_id, streams=self.streams)
        print(f'{Fore.GREEN}success{Style.RESET_ALL}: {result['success']}')
        print(f'{Fore.RED}failure{Style.RESET_ALL}: {result['failure']}')


client_id = ''
client_secret = ''
debug = False

demo = Demo(client_id, client_secret, debug)

demo.authorize_user()
demo.display_user_info()

demo.show_subjects()
if demo.subject_index == -1:
    demo.create_subject()
else:
    demo.select_subject()

demo.display_subject_info()

demo.show_records()
if demo.record_index == -1:
    demo.create_record()
else:
    demo.display_record_info()

demo.cortex.close()
