"""Implementation of the class Database, wrapping a pandas dataframe
for specific services to Biogeme

:author: Michel Bierlaire

:date: Tue Mar 26 16:42:54 2019

"""

# There seems to be a bug in PyLint.
# pylint: disable=invalid-unary-operand-type, too-many-function-args

# Too constraining
# pylint: disable=invalid-name, too-many-arguments, too-many-locals, too-many-statements, too-many-branches, too-many-instance-attributes, too-many-lines, too-many-public-methods

import numpy as np
import pandas as pd

import biogeme.exceptions as excep
import biogeme.filenames as bf
import biogeme.draws as draws
import biogeme.messaging as msg
import biogeme.tools as tools

from biogeme.expressions import Variable, isNumeric, Numeric


class Database:
    """Class that contains and prepare the database."""

    def __init__(self, name, pandasDatabase):
        """Constructor

        :param name: name of the database.
        :type name: string

        :param pandasDatabase: data stored in a pandas data frame.
        :type pandasDatabase: pandas.DataFrame

        """
        self.logger = msg.bioMessage()
        ## Name of the database. Used mainly for the file name when dumping data.
        self.name = name

        ## Pandas data frame containing the data.
        self.data = pandasDatabase
        self.fullData = pandasDatabase

        ## self.variables is initialized by _generateHeaders()
        self.variables = None
        self._generateHeaders()

        ## Number of observations removed by the function Database.remove
        self.excludedData = 0

        ## Name of the column identifying the individuals in a panel
        ## data context. None if data is not panel.
        self.panelColumn = None

        ## map identifying the range of observations for each
        ## individual in a panel data context. None if data is not
        ## panel.
        self.individualMap = None
        self.fullIndividualMap = None

        ## Initialize the dictionary containing random number
        ## generators with a series of native generators.
        self._initNativeRandomNumberGenerators()

        ## Dictionary containing user defined random number
        ## generators. Defined by the function
        ## Database.setRandomNumberGenerators that checks that
        ## reserved keywords are not used. The element of the
        ## dictionary is a tuple with two elements: (0) the function
        ## generating the draws, and (1) a string describing the type of draws
        self.userRandomNumberGenerators = dict()

        ## Number of draws generated by the function Database.generateDraws.
        ## Value 0 if this function is not called.
        self.numberOfDraws = 0
        ## Types of draws for Monte Carlo integration
        self.typesOfDraws = {}

        self._auditDone = False

        ## Draws for Monte-Carlo integration
        self.theDraws = None

        ## Availability expression to check
        self._avail = None

        ## Choice expression to check
        self._choice = None

        ## Expression to check
        self._expression = None

        listOfErrors, listOfWarnings = self._audit()
        if listOfWarnings:
            self.logger.warning('\n'.join(listOfWarnings))
        if listOfErrors:
            self.logger.warning('\n'.join(listOfErrors))
            raise excep.biogemeError('\n'.join(listOfErrors))

    def _initNativeRandomNumberGenerators(self):
        def uniform_antithetic(sampleSize, numberOfDraws):
            return draws.getAntithetic(
                draws.getUniform, sampleSize, numberOfDraws
            )

        def halton2(sampleSize, numberOfDraws):
            return draws.getHaltonDraws(
                sampleSize, numberOfDraws, base=2, skip=10
            )

        def halton3(sampleSize, numberOfDraws):
            return draws.getHaltonDraws(
                sampleSize, numberOfDraws, base=3, skip=10
            )

        def halton5(sampleSize, numberOfDraws):
            return draws.getHaltonDraws(
                sampleSize, numberOfDraws, base=5, skip=10
            )

        def MLHS_anti(sampleSize, numberOfDraws):
            return draws.getAntithetic(
                draws.getLatinHypercubeDraws, sampleSize, numberOfDraws
            )

        def symm_uniform(sampleSize, numberOfDraws):
            return draws.getUniform(sampleSize, numberOfDraws, symmetric=True)

        def symm_uniform_antithetic(sampleSize, numberOfDraws):
            R = int(numberOfDraws / 2)
            localDraws = symm_uniform(sampleSize, R)
            return np.concatenate((localDraws, -localDraws), axis=1)

        def symm_halton2(sampleSize, numberOfDraws):
            return draws.getHaltonDraws(
                sampleSize, numberOfDraws, symmetric=True, base=2, skip=10
            )

        def symm_halton3(sampleSize, numberOfDraws):
            return draws.getHaltonDraws(
                sampleSize, numberOfDraws, symmetric=True, base=3, skip=10
            )

        def symm_halton5(sampleSize, numberOfDraws):
            return draws.getHaltonDraws(
                sampleSize, numberOfDraws, symmetric=True, base=5, skip=10
            )

        def symm_MLHS(sampleSize, numberOfDraws):
            return draws.getLatinHypercubeDraws(
                sampleSize, numberOfDraws, symmetric=True
            )

        def symm_MLHS_anti(sampleSize, numberOfDraws):
            R = int(numberOfDraws / 2)
            localDraws = symm_MLHS(sampleSize, R)
            return np.concatenate((localDraws, -localDraws), axis=1)

        def normal_antithetic(sampleSize, numberOfDraws):
            return draws.getNormalWichuraDraws(
                sampleSize=sampleSize,
                numberOfDraws=numberOfDraws,
                antithetic=True,
            )

        def normal_halton2(sampleSize, numberOfDraws):
            unif = draws.getHaltonDraws(
                sampleSize, numberOfDraws, base=2, skip=10
            )
            return draws.getNormalWichuraDraws(
                sampleSize,
                numberOfDraws,
                uniformNumbers=unif,
                antithetic=False,
            )

        def normal_halton3(sampleSize, numberOfDraws):
            unif = draws.getHaltonDraws(
                sampleSize, numberOfDraws, base=2, skip=10
            )
            return draws.getNormalWichuraDraws(
                sampleSize,
                numberOfDraws,
                uniformNumbers=unif,
                antithetic=False,
            )

        def normal_halton5(sampleSize, numberOfDraws):
            unif = draws.getHaltonDraws(
                sampleSize, numberOfDraws, base=2, skip=10
            )
            return draws.getNormalWichuraDraws(
                sampleSize,
                numberOfDraws,
                uniformNumbers=unif,
                antithetic=False,
            )

        def normal_MLHS(sampleSize, numberOfDraws):
            unif = draws.getLatinHypercubeDraws(sampleSize, numberOfDraws)
            return draws.getNormalWichuraDraws(
                sampleSize,
                numberOfDraws,
                uniformNumbers=unif,
                antithetic=False,
            )

        def normal_MLHS_anti(sampleSize, numberOfDraws):
            unif = draws.getLatinHypercubeDraws(
                sampleSize, int(numberOfDraws / 2)
            )
            return draws.getNormalWichuraDraws(
                sampleSize, numberOfDraws, uniformNumbers=unif, antithetic=True
            )

        ## Dictionary containing native random number generators.
        self.nativeRandomNumberGenerators = {
            'UNIFORM': (draws.getUniform, 'Uniform U[0, 1]'),
            'UNIFORM_ANTI': (uniform_antithetic, 'Antithetic uniform U[0, 1]'),
            'UNIFORM_HALTON2': (
                halton2,
                'Halton draws with base 2, skipping the first 10',
            ),
            'UNIFORM_HALTON3': (
                halton3,
                'Halton draws with base 3, skipping the first 10',
            ),
            'UNIFORM_HALTON5': (
                halton5,
                'Halton draws with base 5, skipping the first 10',
            ),
            'UNIFORM_MLHS': (
                draws.getLatinHypercubeDraws,
                'Modified Latin Hypercube Sampling on [0, 1]',
            ),
            'UNIFORM_MLHS_ANTI': (
                MLHS_anti,
                'Antithetic Modified Latin Hypercube Sampling on [0, 1]',
            ),
            'UNIFORMSYM': (symm_uniform, 'Uniform U[-1, 1]'),
            'UNIFORMSYM_ANTI': (
                symm_uniform_antithetic,
                'Antithetic uniform U[-1, 1]',
            ),
            'UNIFORMSYM_HALTON2': (
                symm_halton2,
                'Halton draws on [-1, 1] with base 2, skipping the first 10',
            ),
            'UNIFORMSYM_HALTON3': (
                symm_halton3,
                'Halton draws on [-1, 1] with base 3, skipping the first 10',
            ),
            'UNIFORMSYM_HALTON5': (
                symm_halton5,
                'Halton draws on [-1, 1] with base 5, skipping the first 10',
            ),
            'UNIFORMSYM_MLHS': (
                symm_MLHS,
                'Modified Latin Hypercube Sampling on [-1, 1]',
            ),
            'UNIFORMSYM_MLHS_ANTI': (
                symm_MLHS_anti,
                'Antithetic Modified Latin Hypercube Sampling on [-1, 1]',
            ),
            'NORMAL': (draws.getNormalWichuraDraws, 'Normal N(0, 1) draws'),
            'NORMAL_ANTI': (normal_antithetic, 'Antithetic normal draws'),
            'NORMAL_HALTON2': (
                normal_halton2,
                'Normal draws from Halton base 2 sequence',
            ),
            'NORMAL_HALTON3': (
                normal_halton3,
                'Normal draws from Halton base 3 sequence',
            ),
            'NORMAL_HALTON5': (
                normal_halton5,
                'Normal draws from Halton base 5 sequence',
            ),
            'NORMAL_MLHS': (
                normal_MLHS,
                'Normal draws from Modified Latin Hypercube Sampling',
            ),
            'NORMAL_MLHS_ANTI': (
                normal_MLHS_anti,
                'Antithetic normal draws from Modified Latin Hypercube Sampling',
            ),
        }

    def descriptionOfNativeDraws(self):
        """Describe the draws available draws with Biogeme

        :return: dict, where the keys are the names of the draws,
                 and the value their description

        Example of output::

            {'UNIFORM: Uniform U[0, 1]',
             'UNIFORM_ANTI: Antithetic uniform U[0, 1]'],
             'NORMAL: Normal N(0, 1) draws'}

        :rtype: dict

        """
        return [
            f'{key}: {tuple[1]}'
            for key, tuple in self.nativeRandomNumberGenerators.items()
        ]

    def _audit(self):
        """Performs a series of checks and reports warnings and errors.
          - Check if there are non numerical entries.
          - Check if there are NaN (not a number) entries.
          - Check if there are strings.
          - Check if the numbering of individuals are contiguous (panel data only).

        Returns:
            A tuple of two lists with the results of
            the diagnostic: listOfErrors, listOfWarnings
        """
        listOfErrors = []
        listOfWarnings = []
        if self._auditDone:
            return listOfErrors, listOfWarnings

        for col, dtype in self.data.dtypes.items():
            if not np.issubdtype(dtype, np.number):
                theError = f'Column {col} in the database does contain {dtype}'
                listOfErrors.append(theError)

        if self.data.isnull().values.any():
            theError = (
                'The database contains NaN value(s). '
                'Detect where they are using the function isnan()'
            )
            listOfErrors.append(theError)

        self._auditDone = True
        return listOfErrors, listOfWarnings

    def _generateHeaders(self):
        """Record the names of the headers
        of the database so that they can be used as an object of type
        biogeme.expressions.Expression
        """
        self.variables = {col: Variable(col) for col in self.data.columns}

    def valuesFromDatabase(self, expression):
        """Evaluates an expression for each entry of the database.

        :param expression: expression to evaluate
        :type expression:  biogeme.expressions.Expression.

        :return: numpy series, long as the number of entries
                 in the database, containing the calculated quantities.
        :rtype: numpy.Series

        """
        self._expression = expression

        def functionToApply(row):
            self._expression.setRow(row)
            res = self._expression.getValue()
            return res

        res = self.data.apply(functionToApply, axis=1)
        return res

    def checkAvailabilityOfChosenAlt(self, avail, choice):
        """Check if the chosen alternative is available for each entry in the database.

        :param avail: list of expressions to evaluate the
                      availability conditions for each alternative.
        :type avail: list of biogeme.expressions.Expression
        :param choice: expression for the chosen alternative.
        :type choice: biogeme.expressions.Expression

        :return: numpy series of bool, long as the number of entries
                 in the database, containing True is the chosen alternative is
                 available, False otherwise.
        :rtype: numpy.Series

        """
        self._avail = avail
        self._choice = choice

        def functionToApply(row):
            self._choice.setRow(row)
            chosen = self._choice.getValue()
            try:
                avExpression = self._avail[chosen]
            except IndexError:
                return False
            except KeyError:
                return False
            avExpression.setRow(row)
            av = avExpression.getValue()
            return av != 0

        res = self.data.apply(functionToApply, axis=1)
        return res

    def choiceAvailabilityStatistics(self, avail, choice):
        """Calculates the number of time an alternative is chosen and available

        :param avail: list of expressions to evaluate the
                      availability conditions for each alternative.
        :type avail: list of biogeme.expressions.Expression
        :param choice: expression for the chosen alternative.
        :type choice: biogeme.expressions.Expression

        :return: for each alternative, a tuple containing the number of time it is chosen,
                 and the number of time it is available.
        :rtype: dict(int: (int, int))

        """
        self._avail = avail
        self._choice = choice

        def functionToApply(row):
            self._choice.setRow(row)
            chosen = self._choice.getValue()
            results = [chosen]
            for v in self._avail.values():
                v.setRow(row)
                av = v.getValue()
                results.append(av)
            return pd.Series(
                results, index=['Chosen'] + list(self._avail.keys())
            )

        res = self.data.apply(functionToApply, axis=1)
        theResults = dict()
        for k in self._avail:
            c = (res['Chosen'] == k).sum()
            theResults[k] = c, res[k].sum()
        return theResults

    def sumFromDatabase(self, expression):
        """Calculates the value of an expression for each entry
            in the database, and returns the sum.

        :param expression: expression to evaluate
        :type expression: biogeme.expressions.Expression
        :return: sum of the expressions over the database.
        :rtype: float
        """
        self._expression = expression

        def functionToApply(row):
            self._expression.setRow(row)
            res = self._expression.getValue()
            return res

        res = np.nansum(self.data.apply(functionToApply, axis=1))
        return res

    def scaleColumn(self, column, scale):
        """Multiply an entire column by a scale value

        :param column: name of the column
        :type column: string
        :param scale: value of the scale. All values of the column will
              be multiplied by that scale.
        :type scale: float

        """
        self.data[column] = self.data[column] * scale

    def suggestScaling(self, columns=None, reportAll=False):
        """Suggest a scaling of the variables in the database.

        For each column, :math:`\\delta` is the difference between the
        largest and the smallest value, or one if the difference is
        smaller than one. The level of magnitude is evaluated as a
        power of 10. The suggested scale is the inverse of this value.

        .. math:: s = \\frac{1}{10^{|\\log_{10} \\delta|}}

        where :math:`|x|` is the integer closest to :math:`x`.

        :param columns: list of columns to be considered.
                        If None, all of them will be considered.
        :type columns: list(str)

        :param reportAll: if False, remove entries where the suggested scale is 1, 0.1 or 10
        :type reportAll: bool

        :return: A Pandas dataframe where each row contains the name
                 of the variable and the suggested scale s. Ideally,
                 the column should be multiplied by s.

        :rtype: pandas.DataFrame

        """
        if columns is None:
            columns = self.data.columns
        else:
            for c in columns:
                if not c in self.data:
                    errorMsg = f'Variable {c} not found.'
                    raise excep.biogemeError(errorMsg)

        largestValue = [
            max(np.abs(self.data[col].max()), np.abs(self.data[col].min()))
            for col in columns
        ]
        res = [
            [col, 1 / 10 ** np.round(np.log10(max(1.0, lv))), lv]
            for col, lv in zip(columns, largestValue)
        ]
        df = pd.DataFrame(res, columns=['Column', 'Scale', 'Largest'])
        if not reportAll:
            # Remove entries where the suggested scale is 1, 0.1 or 10
            remove = (df.Scale == 1) | (df.Scale == 0.1) | (df.Scale == 10)
            df.drop(df[remove].index, inplace=True)
        return df

    def sampleWithReplacement(self, size=None):
        """Extract a random sample from the database, with replacement.

        Useful for bootstrapping.

        :param size: size of the sample. If None, a sample of
               the same size as the database will be generated.
               Default: None.
        :type size: int

        :return: pandas dataframe with the sample.
        :rtype: pandas.DataFrame

        """
        if size is None:
            size = len(self.data)
        sample = self.data.iloc[
            np.random.randint(0, len(self.data), size=size)
        ]
        return sample

    def sampleIndividualMapWithReplacement(self, size=None):
        """Extract a random sample of the individual map
            from a panel data database, with replacement.

        Useful for bootstrapping.

        :param size: size of the sample. If None, a sample of
                   the same size as the database will be generated.
                   Default: None.
        :type size: int

        :return: pandas dataframe with the sample.
        :rtype: pandas.DataFrame

        """
        if not self.isPanel():
            errorMsg = (
                'Function sampleIndividualMapWithReplacement'
                ' is available only on panel data.'
            )
            raise excep.biogemeError(errorMsg)

        if size is None:
            size = len(self.individualMap)
        sample = self.individualMap.iloc[
            np.random.randint(0, len(self.individualMap), size=size)
        ]
        return sample

    def sampleWithoutReplacement(
        self, samplingRate, columnWithSamplingWeights=None
    ):
        """Replace the data set by a sample for stochastic algorithms

        :param samplingRate: the proportion of data to include in the sample.
        :type samplingRate: float
        :param columnWithSamplingWeights: name of the column with
              the sampling weights. If None, each row has equal probability.
        :param columnWithSamplingWeights: string

        :return: None
        """
        if self.isPanel():
            if self.fullIndividualMap is None:
                self.fullIndividualMap = self.individualMap
            else:
                # Check if the structure has not been modified since last sample
                if set(self.fullIndividualMap.columns) != set(
                    self.individualMap.columns
                ):
                    message = 'The structure of the database has been modified since last sample. '
                    left = set(self.fullIndividualMap.columns).difference(
                        set(self.individualMap.columns)
                    )
                    if left:
                        message += f' Columns that disappeared: {left}'
                    right = set(self.individualMap.columns).difference(
                        set(self.fullIndividualMap.columns)
                    )
                    if right:
                        message += f' Columns that were added: {right}'
                    raise excep.biogemeError(message)

            self.individualMap = self.fullIndividualMap.sample(
                frac=samplingRate, weights=columnWithSamplingWeights
            )
            theMsg = (
                f'Full data: {self.fullIndividualMap.shape} '
                f'Sampled data: {self.individualMap.shape}'
            )
            self.logger.debug(theMsg)

        else:
            # Cross sectional data
            if self.fullData is None:
                self.fullData = self.data
            else:
                # Check if the structure has not been modified since last sample
                if set(self.fullData.columns) != set(self.data.columns):
                    message = 'The structure of the database has been modified since last sample. '
                    left = set(self.fullData.columns).difference(
                        set(self.data.columns)
                    )
                    if left:
                        message += f' Columns that disappeared: {left}'
                    right = set(self.data.columns).difference(
                        set(self.fullData.columns)
                    )
                    if right:
                        message += f' Columns that were added: {right}'
                    raise excep.biogemeError(message)

            self.data = self.fullData.sample(
                frac=samplingRate, weights=columnWithSamplingWeights
            )
            self.logger.debug(
                f'Full data: {self.fullData.shape} Sampled data: {self.data.shape}'
            )

    def useFullSample(self):
        """Re-establish the full sample for calculation of the likelihood"""
        if self.isPanel():
            if self.fullIndividualMap is None:
                raise excep.biogemeError(
                    'Full panel data set has not been saved.'
                )
            self.individualMap = self.fullIndividualMap
        else:
            if self.fullData is None:
                raise excep.biogemeError('Full data set has not been saved.')
            self.data = self.fullData

    def addColumn(self, expression, column):
        """Add a new column in the database, calculated from an expression.

        :param expression:  expression to evaluate
        :type expression: biogeme.expressions.Expression

        :param column: name of the column to add
        :type column: string

        :return: the added column
        :rtype: numpy.Series

        :raises ValueError: if the column name already exists.

        """
        if column in self.data.columns:
            raise ValueError(
                f'Column {column} already exists in the database {self.name}'
            )

        def functionToApply(row):
            self._expression.setRow(row)
            return self._expression.getValue()

        self._expression = expression
        self.data[column] = self.data.apply(functionToApply, axis=1)
        self.variables[column] = Variable(column)
        return self.data[column]

    def remove(self, expression):
        """Removes from the database all entries such that the value of the expression is not 0.

        :param expression: expression to evaluate
        :type expression: biogeme.expressions.Expression

        """
        columnName = '__bioRemove__'
        if isNumeric(expression):
            self.addColumn(Numeric(expression), columnName)
        else:
            self.addColumn(expression, columnName)
        self.excludedData = len(self.data[self.data[columnName] != 0].index)
        self.data.drop(
            self.data[self.data[columnName] != 0].index, inplace=True
        )
        self.data.drop(columns=[columnName], inplace=True)

    def dumpOnFile(self):
        """Dumps the database in a CSV formatted file.

        :return:  name of the file
        :rtype: string
        """
        theName = f'{self.name}_dumped'
        dataFileName = bf.getNewFileName(theName, 'dat')
        self.data.to_csv(dataFileName, sep='\t', index_label='__rowId')
        self.logger.general(f'File {dataFileName} has been created')
        return dataFileName

    def setRandomNumberGenerators(self, rng):
        """Defines user-defined random numbers generators.

        :param rng: a dictionary of generators. The keys of the dictionary
           characterize the name of the generators, and must be
           different from the pre-defined generators in Biogeme:
           NORMAL, UNIFORM and UNIFORMSYM. The elements of the
           dictionary are functions that take two arguments: the
           number of series to generate (typically, the size of the
           database), and the number of draws per series.
        :type rng: dict

        Example::

            def logNormalDraws(sampleSize, numberOfDraws):
                return np.exp(np.random.randn(sampleSize, numberOfDraws))

            def exponentialDraws(sampleSize, numberOfDraws):
                return -1.0 * np.log(np.random.rand(sampleSize, numberOfDraws))

            # We associate these functions with a name
            dict = {'LOGNORMAL':(logNormalDraws,
                                 'Draws from lognormal distribution'),
                    'EXP':(exponentialDraws,
                           'Draws from exponential distributions')}
            myData.setRandomNumberGenerators(dict)


        """
        for k in self.nativeRandomNumberGenerators:
            if k in rng:
                errorMsg = (
                    f'{k} is a reserved keyword for draws'
                    f' and cannot be used for user-defined '
                    f'generators'
                )
                raise ValueError(errorMsg)

        self.userRandomNumberGenerators = rng

    def generateDraws(self, types, names, numberOfDraws):
        """Generate draws for each variable.


        :param types: A dict indexed by the names of the variables,
                      describing the types of draws. Each of them can
                      be a native type or any type defined by the
                      function database.setRandomNumberGenerators
        :type types: dict

        :param names: the list of names of the variables that require draws to be generated.
        :type names: list of strings

        :param numberOfDraws: number of draws to generate.
        :type numberOfDraws: int

        :return: a 3-dimensional table with draws. The 3 dimensions are

              1. number of individuals
              2. number of draws
              3. number of variables

        :rtype: numpy.array

        Example::

              types = {'randomDraws1': 'NORMAL_MLHS_ANTI',
                       'randomDraws2': 'UNIFORM_MLHS_ANTI',
                       'randomDraws3': 'UNIFORMSYM_MLHS_ANTI'}
              theDrawsTable = myData.generateDraws(types,
                  ['randomDraws1', 'randomDraws2', 'randomDraws3'], 10)

        """

        self.numberOfDraws = numberOfDraws
        # Dimensions of the draw table:
        # 1. number of variables
        # 2. number of individuals
        # 3. number of draws
        listOfDraws = [None] * len(names)
        for i, v in enumerate(names):
            name = v
            drawType = types[name]
            self.typesOfDraws[name] = drawType
            theGenerator = self.nativeRandomNumberGenerators.get(drawType)
            if theGenerator is None:
                theGenerator = self.userRandomNumberGenerators.get(drawType)
                if theGenerator is None:
                    native = self.nativeRandomNumberGenerators
                    user = self.userRandomNumberGenerators
                    errorMsg = (
                        f'Unknown type of draws for '
                        f'variable {name}: {drawType}. '
                        f'Native types: {native}. '
                        f'User defined: {user}'
                    )
                    raise excep.biogemeError(errorMsg)
            listOfDraws[i] = theGenerator[0](
                self.getSampleSize(), numberOfDraws
            )
            if listOfDraws[i].shape != (self.getSampleSize(), numberOfDraws):
                errorMsg = (
                    f'The draw generator for {name} must'
                    f' generate a numpy array of dimensions'
                    f' ({self.getSampleSize()}, {numberOfDraws})'
                    f' instead of {listOfDraws[i].shape}'
                )
                raise excep.biogemeError(errorMsg)

        self.theDraws = np.array(listOfDraws)
        ## Draws as a three-dimensional numpy series. The dimensions are organized to be more
        # suited for calculation.
        # 1. number of individuals
        # 2. number of draws
        # 3. number of variables
        self.theDraws = np.moveaxis(self.theDraws, 0, -1)
        return self.theDraws

    def getNumberOfObservations(self):
        """
          Reports the number of observations in the database.

        Note that it returns the same value, irrespectively
        if the database contains panel data or not.

        :return: Number of observations.
        :rtype: int

        See also:  getSampleSize()
        """
        return self.data.shape[0]

    def getSampleSize(self):
        """Reports the size of the sample.

        If the data is cross-sectional, it is the number of
        observations in the database. If the data is panel, it is the
        number of individuals.

        :return: Sample size.
        :rtype: int

        See also: getNumberOfObservations()

        """
        if self.isPanel():
            return self.individualMap.shape[0]

        return self.data.shape[0]

    def split(self, slices):
        """Prepare estimation and validation sets for validation.

        :param slices: number of slices
        :type slices: int

        :return: list of estimation and validation data sets
        :rtype: list(tuple(pandas.DataFrame, pandas.DataFrame))
        """
        shuffled = self.data.sample(frac=1)
        theSlices = np.array_split(shuffled, slices)
        estimationSets = []
        validationSets = []
        for i, v in enumerate(theSlices):
            estimationSets.append(
                pd.concat(theSlices[:i] + theSlices[i + 1 :])
            )
            validationSets.append(v)
        return zip(estimationSets, validationSets)

    def isPanel(self):
        """Tells if the data is panel or not.

        :return: True if the data is panel.
        :rtype: bool
        """
        return self.panelColumn is not None

    def panel(self, columnName):
        """Defines the data as panel data

        :param columnName: name of the columns that identifies individuals.
        :type columnName: string

        """

        self.panelColumn = columnName

        # Check if the data is organized in consecutive entries
        # Number of groups of data
        nGroups = tools.countNumberOfGroups(self.data, self.panelColumn)
        sortedData = self.data.sort_values(by=[self.panelColumn])
        nIndividuals = tools.countNumberOfGroups(sortedData, self.panelColumn)
        if nGroups != nIndividuals:
            theError = (
                f'The data must be sorted so that the data'
                f' for the same individual are consecutive.'
                f' There are {nIndividuals} individuals '
                f'in the sample, and {nGroups} groups of '
                f'data for column {self.panelColumn}.'
            )
            raise excep.biogemeError(theError)

        self.buildPanelMap()

    def buildPanelMap(self):
        """Sorts the data so that the observations for each individuals are
        contiguous, and builds a map that identifies the range of indices of
        the observations of each individuals.
        """
        if self.panelColumn is not None:
            self.data = self.data.sort_values(by=self.panelColumn)
            # It is necessary to renumber the row to reflect the new ordering
            self.data.index = range(len(self.data.index))
            local_map = dict()
            individuals = self.data[self.panelColumn].unique()
            for i in individuals:
                indices = self.data.loc[self.data[self.panelColumn] == i].index
                local_map[i] = [min(indices), max(indices)]
            self.individualMap = pd.DataFrame(local_map).T
            self.fullIndividualMap = self.individualMap

    def count(self, columnName, value):
        """Counts the number of observations that have a specific value in a
        given column.

        :param columnName: name of the column.
        :type columnName: string
        :param value: value that is seeked.
        :type value: float

        :return: Number of times that the value appears in the column.
        :rtype: int
        """
        return self.data[self.data[columnName] == value].count()[columnName]

    def __str__(self):
        """Allows to print the dabase"""
        result = f'biogeme database {self.name}:\n{self.data}'
        if self.isPanel():
            result += f'\nPanel data\n{self.individualMap}'
        return result
