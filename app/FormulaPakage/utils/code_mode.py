
#функция выводит значение параметра по названию
def get_param_by_name(param_name, selection_result):
    #найти параметр
    for param in selection_result:
        if param["name"] == param_name:
            #нет ли ошибки
            if "error" in param:
                return False
            #вывести
            return param
    #или None
    return None

class CodeParametr:
    # def __init__(self, product_id, param_id):
    #     self.product_id = product_id
    #     self.param = param_id
    
    def make_mixture(self, selection_result, note_params_info, param_info, select_formula_params):
        """
        алгоритм подбора смеси
        """
        # print(selection_result)
        print(note_params_info)
        print(select_formula_params)
        #чтобы не падала ошибка табличного подбора
        debug_param = {
            "id" : -1,
            "debug" : False,
            'visibility': False
        }
        naydeno = False
        is_mixture = False

        # поиск смеси среди выбранных значений
        if select_formula_params != []:
            for param in select_formula_params:
                if param["name"] == "Смесь":
                    naydeno = True

                    if param["response_value"] == "Да":
                        mixture = {
                            'id': 0,
                            'name': note_params_info['name'],
                            'description': note_params_info["description"],
                            'visibility': False,
                            'response_value': 'Да'
                        }

                        selection_result.append(mixture)
                        is_mixture = True

                    elif param["response_value"] == "Нет":
                        
                        mixture = {
                            'id': param_info.id,
                            'name': param_info.name,
                            'description': param_info.description,
                            'visibility': False,
                            'response_value': 'Нет'
                        }
                        selection_result.append(mixture)

                        return {"total_change" : selection_result}

        # внедрить параметр для смеси на какое-нибудь место, если её ещё нет
        if not naydeno:
            selection_result = [
                debug_param,
                {
                    'id': param_info.id,
                    'name': param_info.name,
                    'description': param_info.description,
                    'visibility': True,
                    'required_type':  "list",
                    "all_values": [
                        "Да",
                        "Нет"
                    ]
                }
            ]
        
        #заполняем смесь
        if is_mixture:
            #есть ли параметр для состава смесей?
            envs_param = get_param_by_name("Состав смеси", select_formula_params)
            #если нет
            if envs_param is None:
                #список ВСЕХ сред
                all_envs_names = get_param_by_name("Название рабочей среды", selection_result)["all_values"]

                #создать
                envs_values = {
                    'id': 1,
                    'name': "Состав смеси",
                    'description': "Нужно выбрать состав смеси из списка доступных сред и указать их мольные доли (%)",
                    "code_example" : [{ "Азот" : 50}, {"Воздух" : 50}],
                    'visibility': True,
                    'required_type':  "select-input",
                    "all_values": all_envs_names
                }

                selection_result = [debug_param, mixture, envs_values]
            
            #если есть
            elif envs_param:
                #проверить правильность
                envs = envs_param["response_value"]
                #выбраны ли среды?
                print(envs_param)
                r_sum = sum(list(env.values())[0] for env in envs)

                if envs == [] or len(envs) == 1:
                    envs_values = {
                        'id': 1,
                        'name': "Состав смеси",
                        'description': "Нужно выбрать состав смеси из списка доступных сред и указать их мольные доли (%)",
                        "code_example" : [{ "Азот" : 50}, {"Воздух" : 50}],
                        'visibility': True,
                        'required_type':  "select-input",
                        "all_values": all_envs_names,
                        "response_value" : envs,
                        "error" : "Смесь не может состоять менее чем из двух сред!"
                    }

                    selection_result = [debug_param, mixture, envs_values]

                
                elif r_sum != 100:
                    envs_values = {
                        'id': 1,
                        'name': "Состав смеси",
                        'description': "Нужно выбрать состав смеси из списка доступных сред и указать их мольные доли (%)",
                        "code_example" : [{ "Азот" : 50}, {"Воздух" : 50}],
                        'visibility': True,
                        'required_type':  "select-input",
                        "all_values": all_envs_names,
                        "response_value" : envs,
                        "error" : f"Сумма мольных долей сред смеси должна составлять 100%, а не {r_sum}"
                    }

                    selection_result = [debug_param, mixture, envs_values]


                #если правильно
                
                


            #если среды не выбраны - предложить
            #выбраны - собрать смесь
                

            # если смесь - получить список сред с мольными долями

            # если мольные доли в сууме не образуют 100% - ошибка, надо чтобы было 100
        
         # если климатика не задана - ошибка, надо задать
        #  if "Климатическое исполнение" in param["name"]:
        #         if "response_value" not in param:
        #             return {"error" : "Выберите вариант климатического исполнения"}
        #         else:
        #             climate = param["response_value"]
         # если температура не задана - ошибка, надо задать
        

        #########РАСЧЕТ###########################

        return {"total_change" : selection_result}

def mixture(envs : list, climate : str, T : float):
    result = {
        "name" : "",
        "environment" : "",
        "molecular_weight" : 0,
        "density" : 0,
        "density_ns": 0,
        "material" : "",
        "viscosity" : 0,
        "isobaric_capacity" : 0,
        "molar_mass" : 0,
        "isochoric_capacity" : 0,
        "adiabatic_index" : 0,
        "compressibility_factor" : 1,
    }

    env_type = set()
    for env in envs:
        env_type.add(env["environment"])


    r_max = 0
    #проверка типа среды смеси
    if len(env_type) == 1: #если среда однородная
        result["environment"] = env_type.pop()
        if result["environment"] == "Жидкость": #если среда - жидкость
            ch_den = 0
            zn_den = 0
            pre_viscosity = 0
            for env in envs:
                r = env["r"]
                result["name"] += f"{env['name']}:{r*100}% "
                result["molecular_weight"] += env["molecular_weight"] * r
                ch_den += env["density"] * r
                zn_den += r
                pre_viscosity += log10(env["viscosity"]) * r

                '''
                if r > r_max:
                    # Плотность несущей среды
                    r_max = r
                    result["density_ns"] = env["density"]
                '''


            result["density"] = ch_den/zn_den
            result["density_ns"] = result["density"]
            result["viscosity"] = 10**(pre_viscosity)
            
            '''
            #добавить подбор материала result["material"]
            if "Морская вода" in result["name"]:
                result["material"] = "12Х18Н12М3ТЛ"
            elif ("Масло подсолнечное" in result["name"]) or ("Лимонная кислота" in result["name"]) or ("Молочная кислота" in result["name"]):
                result["material"] = "12Х18Н9ТЛ"
            '''

        elif result["environment"] == "Газ": #если среда - газ
            viscosity_сh = 0
            viscosity_zn = 0
            pre_M = 0
            adiabatic_index = 0
            adiabatic_index_zn = 0
            density_ns_zn = 0
            for env in envs:
                r = env["r"]
                result["name"] += f"{env['name']}:{r*100}% "
                M_i = env["molar_mass"]
                u_i = env["viscosity"]
                pre_M += M_i * r
                viscosity_сh += u_i * r * sqrt(M_i)
                viscosity_zn += r * sqrt(M_i)
                adiabatic_index += env['adiabatic_index'] * r

                # плотность при н.у.
                result["density_ns"] += (M_i * r)
                #density_ns_zn += r
                '''
                if r > r_max:
                    # Плотность несущей среды
                    r_max = r
                    result["density_ns"] = ((env["molar_mass"] / 22.4) * r) / r
                '''
                
            result["molar_mass"] = pre_M #/100
            result["viscosity"] = viscosity_сh / viscosity_zn
            result["adiabatic_index"] = adiabatic_index

            # плотность при н.у.
            result["density_ns"] = result["density_ns"] / 22.4
            result["density"] = None
            #result["density"] = result["density_ns"] * (273.15) / (T + 273.15)

            print()



    else:
        result["environment"] = "Смесь"
        density_ch = 0
        density_zn = 0
        pre_u = 0
        for env in envs:

            r = env["r"]
            result["name"] += f"{env['name']}:{r*100}% "

            # pre_viscosity += log10(env["viscosity"]) * r

            if env["environment"] == "Газ":
                M = env["molar_mass"]
                density_ch += (env["molar_mass"] / 22.4) * r
                density_zn += r
            elif env["environment"] == "Жидкость":
                M = env["molecular_weight"]
                density_ch += env["density"] * r
                density_zn += r

            pre_u += r * env["viscosity"] * M

            if r > r_max:
                # Плотность несущей среды при нормальных условиях
                r_max = r
                result["density_ns"] = density_ch / density_zn

        #рабочая плотность
        result["density"] = density_ch / density_zn
        result["viscosity"] = pre_u
        # result["viscosity"] = 10**(pre_viscosity)


    material = []
    for env in envs:
        if env['name'] == 'Сероводород' and r < 0.06 and result["environment"] == "Смесь":
            material.append(f"25Л")
        else:
            material.append(env['material'])

    ln = 0
    for mat in material:
        if len(mat) > ln:
            ln = len(mat)
            result["material"] = mat

    #если климатика => то материал
    if ((climate == "ХЛ1") or (climate == "УХЛ1")) and (result["material"] == "25Л"):
        if T < 350.0:
            result["material"] = "20ГЛ"
        elif T >= 350.0 and climate == "ХЛ1":
            result["material"] = "12Х18Н9ТЛ"

    result["T"] = T

    return result

ALLOWED_FUNCTIONS =  [method for method in dir(CodeParametr) if callable(getattr(CodeParametr, method)) and not method.startswith("__")]