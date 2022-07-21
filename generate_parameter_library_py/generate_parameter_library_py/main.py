#!/usr/bin/env python3

import yaml
from yaml.parser import ParserError
import sys
import os
from typing import Callable, Optional
from typeguard import typechecked
from jinja2 import Template
from cpptypes import *


def get_all_templates():
    template_path = os.path.join(os.path.dirname(__file__), 'jinja_templates')
    template_map = dict()
    for file_name in [f for f in os.listdir(template_path) if os.path.isfile(os.path.join(template_path, f))]:
        with open(os.path.join(template_path, file_name)) as file:
            template_map[file_name] = file.read()

    return template_map


# class to help minimize string copies
class Buffer:
    def __init__(self):
        self.data_ = bytearray()

    def __iadd__(self, element):
        self.data_.extend(element.encode())
        return self

    def __str__(self):
        return self.data_.decode()


class YAMLSyntaxError(Exception):
    """Raised when the input value is too large"""

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


@typechecked
def compile_error(msg: str):
    return YAMLSyntaxError("\nERROR: " + msg)


@typechecked
def array_type(defined_type: str):
    return defined_type.__contains__("array")


@typechecked
def validate_type(defined_type: str, value):
    type_translation = {"string": str,
                        "double": float,
                        "int": int,
                        "bool": bool,
                        "string_array": str,
                        "double_array": float,
                        "int_array": int,
                        "bool_array": bool}

    if isinstance(value, list):
        if not array_type(defined_type):
            return False
        for val in value:
            if type_translation[defined_type] != type(val):
                return False
    else:
        if array_type(defined_type):
            return False
        if type_translation[defined_type] != type(value):
            return False

    return True


# value to c++ string conversion functions
@typechecked
def bool_to_str(cond: Optional[bool]):
    if cond is None:
        return None
    return "true" if cond else "false"


@typechecked
def float_to_str(num: Optional[float]):
    if num is None:
        return None
    str_num = str(num)
    if str_num == "nan":
        str_num = "std::numeric_limits<double>::quiet_NaN()"
    elif str_num == "inf":
        str_num = "std::numeric_limits<double>::infinity()"
    elif str_num == "-inf":
        str_num = "-std::numeric_limits<double>::infinity()"
    else:
        if len(str_num.split('.')) == 1:
            str_num += ".0"

    return str_num


@typechecked
def int_to_str(num: Optional[int]):
    if num is None:
        return None
    return str(num)


@typechecked
def str_to_str(s: Optional[str]):
    if s is None:
        return None
    return "\"%s\"" % s


# cpp_type, val_to_cpp_str, parameter_conversion
@typechecked
def get_translation_data(defined_type: str) -> (str, Callable, str):
    if defined_type == 'string_array':
        cpp_type = 'std::string'
        parameter_conversion = 'as_string_array()'
        val_to_cpp_str = str_to_str

    elif defined_type == 'double_array':
        cpp_type = 'double'
        parameter_conversion = 'as_double_array()'
        val_to_cpp_str = float_to_str

    elif defined_type == 'int_array':
        cpp_type = 'int'
        parameter_conversion = 'as_integer_array()'
        val_to_cpp_str = int_to_str

    elif defined_type == 'bool_array':
        cpp_type = 'bool'
        parameter_conversion = 'as_bool_array()'
        val_to_cpp_str = bool_to_str

    elif defined_type == 'string':
        cpp_type = 'std::string'
        parameter_conversion = 'as_string()'
        val_to_cpp_str = str_to_str

    elif defined_type == 'double':
        cpp_type = 'double'
        parameter_conversion = 'as_double()'
        val_to_cpp_str = float_to_str

    elif defined_type == 'integer':
        cpp_type = 'int'
        parameter_conversion = 'as_int()'
        val_to_cpp_str = int_to_str

    elif defined_type == 'bool':
        cpp_type = 'bool'
        parameter_conversion = 'as_bool()'
        val_to_cpp_str = bool_to_str

    else:
        raise compile_error('invalid yaml type: %s' % type(defined_type))

    return cpp_type, val_to_cpp_str, parameter_conversion


# cpp_type, val_to_cpp_str, parameter_conversion
@typechecked
def get_cpp_type(yaml_type: str) -> (str, Callable, str):
    if yaml_type == 'string_array':
        cpp_type = 'std::vector<std::string>'
    elif yaml_type == 'double_array':
        cpp_type = 'std::vector<double>'
    elif yaml_type == 'int_array':
        cpp_type = 'std::vector<int>'
    elif yaml_type == 'bool_array':
        cpp_type = 'std::vector<bool>'
    elif yaml_type == 'string':
        cpp_type = 'std::string'
    elif yaml_type == 'double':
        cpp_type = 'double'
    elif yaml_type == 'integer':
        cpp_type = 'int'
    elif yaml_type == 'bool':
        cpp_type = 'bool'
    else:
        raise compile_error('invalid yaml type: %s' % type(yaml_type))

    return cpp_type


# cpp_type, val_to_cpp_str, parameter_conversion
@typechecked
def get_val_to_cpp_str_func(yaml_type: str) -> Callable:
    if yaml_type == 'string_array':
        val_to_cpp_str = str_to_str
    elif yaml_type == 'double_array':
        val_to_cpp_str = float_to_str
    elif yaml_type == 'int_array':
        val_to_cpp_str = int_to_str
    elif yaml_type == 'bool_array':
        val_to_cpp_str = bool_to_str
    elif yaml_type == 'string':
        val_to_cpp_str = str_to_str
    elif yaml_type == 'double':
        val_to_cpp_str = float_to_str
    elif yaml_type == 'integer':
        val_to_cpp_str = int_to_str
    elif yaml_type == 'bool':
        val_to_cpp_str = bool_to_str
    else:
        raise compile_error('invalid yaml type: %s' % type(yaml_type))

    return val_to_cpp_str


@typechecked
def get_parameter_conversion_function(yaml_type: str) -> str:
    if yaml_type == 'string_array':
        parameter_conversion = 'as_string_array()'
    elif yaml_type == 'double_array':
        parameter_conversion = 'as_double_array()'
    elif yaml_type == 'int_array':
        parameter_conversion = 'as_integer_array()'
    elif yaml_type == 'bool_array':
        parameter_conversion = 'as_bool_array()'
    elif yaml_type == 'string':
        parameter_conversion = 'as_string()'
    elif yaml_type == 'double':
        parameter_conversion = 'as_double()'
    elif yaml_type == 'integer':
        parameter_conversion = 'as_int()'
    elif yaml_type == 'bool':
        parameter_conversion = 'as_bool()'
    else:
        raise compile_error('invalid yaml type: %s' % type(yaml_type))

    return parameter_conversion


@typechecked
def get_validation_translation(validation_functions: list[list[any]]):
    if not isinstance(validation_functions[0], list):
        validation_functions = [validation_functions]
    for validation_function in validation_functions:
        if len(validation_function) < 2:
            raise compile_error(
                "The user yaml defined validation function %s does not have enough input arguments, requires at least 1." %
                validation_function[0])
        for ind, arg in enumerate(validation_function[1:]):
            if isinstance(arg, list):
                raise compile_error(
                    "The user yaml defined validation function %s uses a list input argument which is not supported" %
                    validation_function[0])

            if isinstance(arg, int):
                val_to_cpp_str = int_to_str
            elif isinstance(arg, float):
                val_to_cpp_str = float_to_str
            elif isinstance(arg, bool):
                val_to_cpp_str = bool_to_str
            elif isinstance(arg, str):
                val_to_cpp_str = str_to_str
            else:
                raise compile_error('invalid python type pass to get_validation_translation, type: %s' % type(arg))

            validation_function[ind + 1] = val_to_cpp_str(arg)

    return validation_functions


@typechecked
def declare_struct(defined_type: str, cpp_type: str, name: str, default_value: list) -> str:
    code_str = Buffer()
    if array_type(defined_type):
        code_str += "std::vector<%s> %s_ " % (cpp_type, name)
        if len(default_value) > 0:
            code_str += "= {"
            for ind, val in enumerate(default_value[:-1]):
                code_str += "%s, " % val
            code_str += "};\n"
        else:
            code_str += ";\n"
    else:
        if len(default_value) > 0:
            code_str += "%s %s_ = %s;\n" % (cpp_type, name, default_value[0])
        else:
            code_str += "%s %s_;\n" % (cpp_type, name)
    return str(code_str)


@typechecked
def if_else_statement(effects_true, effects_false, conditions, bool_operators) -> str:
    code_str = Buffer()
    code_str += "if ("
    code_str += conditions[0]
    for ind, condition in enumerate(conditions[1:]):
        code_str += bool_operators[ind]
        code_str += condition
    code_str += ") {\n"
    for effect in effects_true:
        code_str += effect
    if len(effects_false) > 0:
        code_str += "} else {"
        for effect in effects_false:
            code_str += effect
    code_str += "}\n"

    return str(code_str)


@typechecked
def if_statement(effects, conditions, bool_operators) -> str:
    return if_else_statement(effects, [], conditions, bool_operators)


@typechecked
def flatten_effects(effects) -> str:
    code_str = Buffer()
    for effect in effects:
        code_str += effect

    return str(code_str)


@typechecked
def scoped_codeblock(effects) -> str:
    code_str = Buffer()
    code_str += "{\n"
    code_str += flatten_effects(effects)
    code_str += "}\n"
    return str(code_str)


@typechecked
def function_call(namespace: str, func_name: str, args: list[str]) -> str:
    code_str = Buffer()
    code_str += namespace + "::" + func_name
    code_str += "("
    for ind, arg in enumerate(args):
        code_str += arg
        if ind < len(args) - 1:
            code_str += ", "
    code_str += ")"

    return str(code_str)


@typechecked
def validation_sequence(namespace: str, func_name: str, args: list, effects_true: list[str], effects_false: list[str]):
    # assumes that the validation function is named validate_{defined_type}_{method}
    if len(args) == 0:
        return flatten_effects(effects_true)  # no validation needed
    tmp = ["param"]
    tmp.extend(args)
    args = tmp
    code_str = Buffer()
    code_str += "validation_result = "
    code_str += function_call(namespace, func_name, args)
    code_str += ";\n"

    conditions = ["validation_result.success()"]
    code_str += if_else_statement(effects_true, effects_false, conditions, [])

    return str(code_str)


@typechecked
def default_validation(effects: list[str], defined_type: str, fixed_size: list, bounds: list) -> str:
    code_str = Buffer()
    effects_false = ["result.reason = validation_result.error_msg();\n",
                     "result.successful = false;"]
    if fixed_size:
        effects2 = [
            validation_sequence("gen_param_struct_validators", "validate_" + defined_type + "_len", fixed_size,
                                effects,
                                effects_false)]
    else:
        effects2 = effects
    if bounds:
        code_str += validation_sequence("gen_param_struct_validators", "validate_" + defined_type + "_bounds", bounds,
                                        effects2,
                                        effects_false)
    else:
        code_str += flatten_effects(effects2)

    return str(code_str)


# class used to fill template text file with passed in yaml file
class GenParamStruct:
    templates = get_all_templates()

    def __init__(self):
        self.contents = Buffer()
        self.struct = Buffer()
        self.param_set = Buffer()
        self.param_describe = Buffer()
        self.param_get = Buffer()
        self.namespace = ""
        self.struct_tree = Struct("Params", [])
        self.declare_params = []
        self.update_parameters = []
        self.declare_parameters = []
        self.declare_parameter_sets = []

    def parse_params(self, name, value, nested_name_list):
        # define names for parameters and variables
        nested_name = "".join(x + "_." for x in nested_name_list[1:])
        param_prefix = "p_" + "".join(x + "_" for x in nested_name_list[1:])
        param_name = "".join(x + "." for x in nested_name_list[1:]) + name

        # required attributes
        try:
            defined_type = value['type']
        except KeyError as e:
            raise compile_error("No type defined for parameter %s" % param_name)

        # optional attributes
        default_value = value.get('default_value', None)
        description = value.get('description', '')
        read_only = bool(value.get('read_only', False))
        bounds = value.get('bounds', [])
        fixed_size = value.get('fixed_size', [])
        validations = value.get('validation', [])
        if len(validations) > 0 and isinstance(validations[0], str):
            validations = [validations]

        # cpp_type, val_to_cpp_str, parameter_conversion = get_translation_data(defined_type)

        parameter_conversion = get_parameter_conversion_function(defined_type)

        # define struct
        var = VariableDeclaration(defined_type, name, default_value)
        self.struct_tree.add_field(var)

        declare_parameter = DeclareParameter(param_name, description, read_only, defined_type, default_value)
        self.declare_parameters.append(declare_parameter)

        update_parameter_invalid = "result.successful = false;\nbreak;"
        update_parameter_valid = ""
        update_parameter = UpdateParameter(param_name, parameter_conversion)
        for validation in validations:
            validation_function = ValidationFunction(validation[0], validation[1:])
            parameter_validation = ParameterValidation(update_parameter_invalid, update_parameter_valid, validation_function)
            update_parameter.add_parameter_validation(parameter_validation)

        self.update_parameters.append(update_parameter)

        # TODO fix these effects
        declare_parameter_invalid = 'throw rclcpp::exceptions::InvalidParameterValueException("Invalid value set during initialization for parameter gravity_compensation.CoG.pos ");'
        declare_parameter_valid = "params_.gravity_compensation_.CoG_.pos_ = param.as_double_array();"
        declare_parameter_set = DeclareParameterSet(param_name, parameter_conversion)
        for validation in validations:
            validation_function = ValidationFunction(validation[0], validation[1:])
            parameter_validation = ParameterValidation(declare_parameter_invalid, declare_parameter_valid,
                                                       validation_function)
            declare_parameter_set.add_parameter_validation(parameter_validation)

        self.declare_parameter_sets.append(declare_parameter_set)

        # # validate inputs
        # if bounds and not validate_type(defined_type, bounds):
        #     raise compile_error("The type of the bounds must be the same type as the defined type")
        # if default_value and not validate_type(defined_type, default_value):
        #     raise compile_error("The type of the default_value must be the same type as the defined type")
        # if fixed_size and not isinstance(fixed_size, int):
        #     raise compile_error("The type of the fixed size attribute must be an integer")
        #
        # # get translation variables from defined value type
        # cpp_type, val_to_cpp_str, parameter_conversion = get_translation_data(defined_type)
        #
        # # convert python types to lists of inputs
        # if default_value:
        #     if array_type(defined_type):
        #         for i in range(len(default_value)):
        #             default_value[i] = val_to_cpp_str(default_value[i])
        #     else:
        #         default_value = [val_to_cpp_str(default_value)]
        # else:
        #     default_value = []
        # if bounds:
        #     for i in range(len(bounds)):
        #         bounds[i] = val_to_cpp_str(bounds[i])
        # else:
        #     bounds = []
        # if fixed_size:
        #     fixed_size = [int_to_str(fixed_size)]
        # else:
        #     fixed_size = []
        # if read_only:
        #     read_only = [read_only]
        # else:
        #     read_only = []
        # if validation:
        #     if not isinstance(validation[0], list):
        #         validation = [validation]
        #     validation = get_validation_translation(validation)
        # else:
        #     validation = []

        # self.struct += declare_struct(defined_type, cpp_type, name, default_value)
        #
        # # set param value if param.name is the parameter being updated
        # param_set_effects = ["params_.%s_ = param.%s;\n" % (nested_name + name, parameter_conversion),
        #                      "result.successful = true;\n"]
        # param_set_conditions = ["param.get_name() == " + "\"%s\" " % param_name]
        # code_str = default_validation(param_set_effects, defined_type, fixed_size, bounds)
        # self.param_set += if_statement(code_str, param_set_conditions, [])
        # parameter_name: str, parameter_description: str, parameter_read_only: bool, parameter_type: str):

        # # create parameter description
        # param_describe_effects = ["rcl_interfaces::msg::ParameterDescriptor descriptor;\n",
        #                           "descriptor.description = \"%s\";\n" % description]
        # if len(bounds):
        #     param_describe_effects.extend([
        #         "rcl_interfaces::msg::FloatingPointRange range;\n",
        #         "range.from_value = %s;\n" % bounds[0],
        #         "range.to_value = %s;\n" % bounds[1],
        #         "descriptor.floating_point_range.push_back(range);\n"
        #     ])
        # if len(read_only):
        #     param_describe_effects.extend([
        #         "descriptor.read_only = %s;\n" % bool_to_str(read_only[0]),
        #     ])
        # if len(default_value):
        #     value_str = "rclcpp::ParameterValue(params_.%s_)" % (nested_name + name)
        # else:
        #     value_str = "rclcpp::ParameterType::PARAMETER_%s" % defined_type.upper()
        #
        # param_describe_effects_2 = ["auto %s = %s;\n" % (param_prefix + name, value_str),
        #                             "parameters_interface->declare_parameter(\"%s\", %s, descriptor);\n" % (
        #                                 param_name, param_prefix + name)]
        # param_describe_conditions = ["!parameters_interface->has_parameter(\"%s\")" % param_name]
        #
        # param_describe_effects.append(
        #     if_statement(param_describe_effects_2, param_describe_conditions, [])
        # )
        # self.param_describe += scoped_codeblock(param_describe_effects)

        # UNCOMMENT
        # self.declare_params.append(DeclareParameter(param_name, description, read_only, defined_type))

        # get parameter from by calling parameters_interface API
        # self.param_get += "param = parameters_interface->get_parameter(\"%s\");\n" % param_name
        # param_get_effect_false = ["throw rclcpp::exceptions::InvalidParameterValueException(\"Invalid value set during "
        #                           "initialization for parameter %s: \" + validation_result.error_msg());" % param_name]
        # param_get_effect_true = ["params_.%s_ = param.%s;\n" % (
        #     nested_name + name, parameter_conversion)]
        #
        # # add default validation
        # code_str = validation_sequence("gen_param_struct_validators", "validate_" + defined_type + "_len", fixed_size,
        #                                param_get_effect_true,
        #                                param_get_effect_false)
        # code_str = validation_sequence("gen_param_struct_validators", "validate_" + defined_type + "_bounds", bounds,
        #                                [code_str],
        #                                param_get_effect_false)
        # # add custom validation
        # for val in validation:
        #     code_str = validation_sequence("gen_param_struct_validators", val[0], val[1:], [code_str],
        #                                    param_get_effect_false)
        #
        # self.param_get += code_str

    def parse_dict(self, name, root_map, nested_name):

        if isinstance(root_map, dict) and isinstance(next(iter(root_map.values())), dict):
            cur_struct_tree = self.struct_tree

            if name != self.namespace:
                self.struct += "struct %s {\n" % name
                sub_struct = Struct(name, [])
                self.struct_tree.add_sub_struct(sub_struct)
                self.struct_tree = sub_struct
            for key in root_map:
                if isinstance(root_map[key], dict):
                    nested_name.append(name)
                    self.parse_dict(key, root_map[key], nested_name)
                    nested_name.pop()
            if name != self.namespace:
                self.struct += "} %s_;\n" % name

            self.struct_tree = cur_struct_tree
        else:
            self.parse_params(name, root_map, nested_name)

    def run(self):
        if len(sys.argv) < 3 and len(sys.argv) > 4:
            raise compile_error("generate_parameter_library_py expects three input argument: output_file, "
                                "yaml file path, [validate include header]")

        param_gen_directory = sys.argv[0].split("/")
        param_gen_directory = "".join(x + "/" for x in param_gen_directory[:-1])
        if param_gen_directory[-1] != "/":
            param_gen_directory += "/"

        output_file = sys.argv[1]
        output_dir = os.path.dirname(output_file)
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)

        yaml_file = sys.argv[2]
        with open(yaml_file) as f:
            try:
                docs = yaml.load_all(f, Loader=yaml.FullLoader)
                doc = list(docs)[0]
            except ParserError as e:
                raise compile_error(str(e))

            if len(doc) != 1:
                raise compile_error("the controller yaml definition must only have one root element")
            self.namespace = list(doc.keys())[0]
            self.parse_dict(self.namespace, doc[self.namespace], [])

        USER_VALIDATORS = ""
        if (len(sys.argv) > 3):
            user_validation_file = sys.argv[3]
            with open(user_validation_file, 'r') as f:
                USER_VALIDATORS = f.read()

        COMMENTS = "// this is auto-generated code "
        NAMESPACE = self.namespace

        # template_file = os.path.join(
        #     os.path.dirname(__file__), 'cpp_templates', 'template.txt')
        # with open(template_file, "r") as f:
        #     self.contents = f.read()

        validation_functions_file = os.path.join(
            os.path.dirname(__file__), 'cpp_templates', 'validators.hpp')
        with open(validation_functions_file, "r") as f:
            VALIDATION_FUNCTIONS = f.read()

        template_path = os.path.join(os.path.dirname(__file__), 'jinja_templates')
        template_map = dict()
        for file_name in [f for f in os.listdir(template_path) if os.path.isfile(os.path.join(template_path, f))]:
            with open(os.path.join(template_path, file_name)) as file:
                template_map[file_name] = file.read()

        data = {'USER_VALIDATORS': USER_VALIDATORS,
                'COMMENTS': COMMENTS,
                'namespace': NAMESPACE,
                'validation_functions': VALIDATION_FUNCTIONS,
                'struct_content': self.struct_tree.inner_content(),
                'update_params_set': "\n".join([str(x) for x in self.update_parameters]),
                'declare_params': "\n".join([str(x) for x in self.declare_parameters]),
                'declare_params_set': "\n".join([str(x) for x in self.declare_parameter_sets])}

        j2_template = Template(template_map['parameter_listener'])
        # self.contents += j2_template.render(data)

        # self.contents = self.contents.replace("**COMMENTS**", COMMENTS)
        # self.contents = self.contents.replace("**USER VALIDATORS**", USER_VALIDATORS)
        # self.contents = self.contents.replace("**NAMESPACE**", NAMESPACE)
        # self.contents = self.contents.replace("**STRUCT_CONTENT**", str(self.struct))
        # self.contents = self.contents.replace("**PARAM_SET**", str(self.param_set))
        # self.contents = self.contents.replace("**DESCRIBE_PARAMS**", str(self.param_describe))
        # self.contents = self.contents.replace("**GET_PARAMS**", str(self.param_get))
        code = j2_template.render(data)
        with open(output_file, "w") as f:
            f.write(code)


def main():
    gen_param_struct = GenParamStruct()
    gen_param_struct.run()
    pass


if __name__ == "__main__":
    sys.exit(main())
