import os.path
import sqlite3
import pandas

class cdb:
    """Cinema Database Class

    Class that loads, verifies and manages access to a Cinema Database.

    Two important definitions are:
    - parameter path: A slash-separated string that defines an ordered set of 
      parameters that designate a set of extracts.
    	- Example: `/phi/theta/variable`
    - extract path: A specific instance of a *parameter path*, giving values 
      for each parameter.
        - Example: `/0/90/temperature`
    """

    def __init__(self, path):
        """Cinema Database class constructor
        """

        self.tablename = "CINEMA"
        self.path      = path
        self.datapath  = os.path.join(self.path, "data.csv")
        self.extracts  = {} 
        self.parameternames = []
        self.extractnames   = []

        # create the internal data structures needed
        self.con = sqlite3.connect(":memory:")
        self.DBinitialized = False


    def read_data_from_file(self):
        """Read in a Cinema database.

        Returns true on success, false on failure
        """
        result = self.check_database() 

        # TODO: check state, and make sure it isn't initialized yet.
        if result:
            cur = self.con.cursor()
            df = pandas.read_csv(self.datapath, na_filter=False)
            self.parameternames = list(df.columns)
            df.to_sql(self.tablename, self.con, if_exists='replace', index=False)

        return result

    def parameter_exists(self, parameter):
        """Check if a parameter exists
        """
        return parameter in self.parameternames

    def extract_parameter_exists(self, parameter):
        """Check if an extract parameter exists
        """
        return parameter in self.extractnames

    def set_extract_parameter_names(self,names):
        """Set the parameter names that are considered extracts
        """
        for n in names:
            self.parameternames.remove(n)
            self.extractnames.append(n)

    def __get_extract_paths(self, parameters):
        """Get an extract path for a set of parameters
        
        An extract path is a string that embodies a set of (key, value) pairs 
        for the parameters in a cinema database. For example, if the parameter 
        path is

           /phi/theta
        
        Then some possible extract paths are:

          /10/10
          /20/24.5
          ...

        These can provide a unique hash for the extracts uniquely defined by 
        the set of values
        """
        query = "SELECT {} from {} WHERE ".format(
                    ", ".join(self.extractnames), self.tablename)
        res = ""
        
        path = "/"
        first = True
        for key in self.parameternames:
            if not first:
                query = query + " AND "
                path = path + "/"
            else:
                first = False

            if key in parameters:
                value = parameters[key]
            else:
                value = Null

            query = query + "{} = \'{}\' ".format(key, value)
            path = path + value  

        return path, query

    def get_extracts(self, parameters):
        """Return the extracts for a set of parameters
        """
        (extract_path, query) = self.__get_extract_paths(parameters)

        cur = self.con.cursor()
        cur.execute(query)

        extracts = [] 
        fullpath = None
        for row in cur.fetchall():
            self.extracts[extract_path] = [] 
            for r in row:
                fullpath = os.path.join(self.path, r)
                self.extracts[extract_path].append(fullpath)
                extracts.append(fullpath)

        return extracts 

    def check_database(self):
        """Check if database exists
        """
        return os.path.exists(self.path) and os.path.exists(self.datapath)

#   def __get_extract_path(self, parameters):
#       (path, query) = self.__get_extract_paths(parameters)
#       return path

#   def __get_extract_query(self, parameters):
#       (path, query) = self.__get_extract_paths(parameters)
#       return query

# ------------------------------------------------------------------------------
#
# ------------------------------------------------------------------------------
    def initialize(self):
        """Create the destination directory and report error if it fails
        """
        result = True

        if not os.path.exists(self.path):
            try:
                os.makedirs(self.path)
            except:
                raise ISError(
                        "Can't create Cinema Database directory: (%s)".format(
                        self.path))
                result = False
        else:
            # TODO: report error that it exists
            result = False

        return result

    def __add_parameter(self, p):
        """Add a paramter name to the database
        """
        if not self.parameter_exists(p):
            self.parameternames.append(p)
            if not self.DBinitialized:
                self.con.cursor().execute("CREATE TABLE {} ({} TEXT)".format(self.tablename, p))
                self.DBinitialized = True

            else:
                self.con.cursor().execute("ALTER TABLE {} ADD {} TEXT".format(self.tablename, p))


    def __generate_insert_command(self, parameters):
        command = """INSERT INTO {} (""".format(self.tablename)

        for p in parameters:
            command = """{}{}, """.format(command, p)
        # remove the last comma and space
        command = command[:-2]
        command = """{}) VALUES(""".format(command)
        for p in parameters:
            command = """{}\"{}\", """.format(command, parameters[p])
        command = command[:-2]
        command = """{})""".format(command)

        return command
# ------------------------------------------------------------------------------
#
# ------------------------------------------------------------------------------
    def add_entry(self, parameters):
        """Add an entry into the database, updating parameters
        """

        for p in parameters:
            self.__add_parameter(p)

        command = self.__generate_insert_command(parameters)
        cursor = self.con.cursor()
        cursor.execute(command)

        return cursor.lastrowid


# ------------------------------------------------------------------------------
#
# ------------------------------------------------------------------------------
    def delete_entry(self, ID):
        """Delete an entry into the database
        """
        self.con.cursor().execute("DELETE FROM {} where rowid={}".format(
                self.tablename, str(ID)))

# ------------------------------------------------------------------------------
#
# ------------------------------------------------------------------------------
    def finalize(self):
        """Write all entries to disk, reconciling each entry's parameters with
           the overall parameter list
        """
        db_df = pandas.read_sql_query("SELECT * FROM {}".format(self.tablename), self.con)
        db_df.to_csv(self.datapath, index=False)
