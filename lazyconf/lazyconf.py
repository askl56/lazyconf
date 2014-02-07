from lib.schema import *
from lib.prompt import *
from lib.select import *
from lib.merge import *

### Lazyconf ###
### Our main class. Annotate public functions better.

class Lazyconf():

    # Initialisation.
    def __init__(self):
        self.prompt = Prompt()
        self.data = None


    # Goes through all the options in the data file, and prompts new values.
    def configure_data(self, data, key_string = ''):
        
        # If there's no keys in this dictionary, we have nothing to do.
        if len(data.keys()) == 0:
            return

        # Split the key string by its dots to find out how deep we are.
        key_parts = key_string.rsplit('.')
        prefix = '  ' * (len(key_parts) - 1)

        # Attempt to get a label for this key string.
        label = self.data.get_label(key_string)

        # If we are have any key string or label, write the header for this section.
        if label:
            p = prefix
            if len(p) > 0:
                p += ' '
            self.prompt.header(p + '[' + label + ']')

        # Add to the prefix to indicate options on this level.
        prefix = prefix + "   "

        # If this section has an '_enabled' key, process it first, as it could enable or disable this whole section.
        if '_enabled' in data.keys():
            s = self.data.get_key_string(key_string, '_enabled')

            #Prompt whether to enable this section. Use the existing value as the default.
            data['_enabled'] = self.prompt.bool(prefix + self.data.get_label(s), data['_enabled'])

            # Return if this section is now disabled.
            if data['_enabled'] is False:
                return

        # Loop through the rest of the dictionary and prompt for every key. If the value is a dictionary, call this function again for the next level.
        for k, v in data.iteritems():

            # If we hit the '_enabled' key, we've already processed it (but still need it in the dictionary for saving). Ignore it.
            if k == '_enabled':
                continue
            
            # Get the type of the value at this key, and the dot-noted format of this key.
            t = type(v)
            s = self.data.get_key_string(key_string, k)

            # See if this key has an associated select. If so, this type is a select type.
            select = self.data.get_select(s)
            if select:
                data[k] = self.prompt.select(prefix + self.data.get_label(s), select, default = v)

            # If the value type is a dictionary, recall this function.
            elif t is dict:
                self.configure_data(v, s)

            # If the value type is a boolean, prompt a boolean.
            elif t is bool:
                data[k] = self.prompt.bool(prefix + self.data.get_label(s), default = v)

            # If the value is an int, prompt and int.
            elif t is int:
                data[k] = self.prompt.int(prefix + self.data.get_label(s), default = v)

            # If someone has put a list in data, we default it to an empty string. If it had come from the schema, it would already be a string.
            elif t is list:
                data[k] = self.prompt.string(prefix + self.data.get_label(s) + ':', default = "")

            # If none of the above are true, it's a string.
            else:
                data[k] = self.prompt.string(prefix + self.data.get_label(s) + ':', default = v)


    # Loads the schema from a schema file.
    def configure(self, schema_file, data_file, out_file):

        # Initialise the schema and data objects.
        schema, data = Schema(), Schema()
        
        # Load the schema from a file.
        try:
            schema.load(schema_file)
        except (Exception, IOError, ValueError) as e:

            # If we can't load the schema, abort.
            self.prompt.error(str(e) + ". Aborting...")
            return
        else:
            self.prompt.success("Loaded schema from " + schema_file)

        # Load the data from a file.
        try:
            data.load(data_file)
        except (Exception, IOError, ValueError) as e:
            self.prompt.error(str(e))

            # If we can't load the data, we can continue from the schema.
            # If the data file path was entered incorrectly, we can abort.
            cont = self.prompt.bool("Continue from schema", True)
            if not cont:
                self.prompt.error("Aborting...")
                return
        else:
            self.prompt.success("Loaded data from " + data_file)

        # Store the internals of the schema (labels, selects, etc.) in data.
        data.internal = schema.internal

        # If we have data from a data file, merge the schema file into it.
        if data.data:

            # Create a new Merge instance using the data from the schema and data files.
            m = Merge(schema.data, data.data)
            mods = m.merge()

            for a in mods['added']:
                print(green("Added " + a + " to data."))

            for r in mods['removed']:
                print(red("Removed " + r + " from data."))

            for k,m in mods['modified']:
                print(blue("Modified " + k + ": " + m[0] + " became " + m[1] + "." ))

        # Otherwise, reference the data from the schema file verbatim.
        else:
            data.data = schema.data

        # Store the data.
        self.data = data

        # Configure the data.
        self.configure_data(data.data)

        # Save the data to the out file.
        self.data.save(out_file)


    # Get the data for a dot-notated key.
    def get(self, key):
        return self.data.get(key)


    def load(self, data_file):

        # Load the data from a file.
        try:
            self.data = Schema().load(data_file)
        except (Exception, IOError, ValueError) as e:
            raise e

        return self