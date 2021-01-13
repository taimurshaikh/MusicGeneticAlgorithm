""" Genetic Algorithm for music generation. Takes a user defined key and tempo and evolves a melody according to those """
import random
from midiutil import MIDIFile

# MIDI information will be encoded  by list of numbers corresponding to note codes

# Dictionary containing the patterns of tones and semitones that a given scale follows (this is for two octaves)
scaleStructures = {
    "major": [2,2,1,2,2,2,1] * 2,
    "minor": [2,1,2,2,1,2,2] * 2,
    "major pentatonic": [2, 2, 3, 2, 3] * 2,
    "minor pentatonic": [3, 2, 2, 3, 2] * 2,
    }

# Dictionary containing the MIDI code for every note starting from A below middle C
startingNotes = {}
a3 = 45
currentCode = a3
for i in "abcdefg":
    startingNotes[i] = currentCode
    # B and E do not have sharps so skip them for this part
    if i != "b" and i != "e":
        startingNotes[f"{i}#"] = currentCode + 1
        currentCode += 2
    # C and F do not have flats so skip them for this part
    if i != "c" and i != "f":
        startingNotes[f"{i}b"] = currentCode - 1
        currentCode += 2
    else:
        currentCode += 1

smoothnessWeight = 10
rhythmWeight = 15

mutationRate = 0.1

def main():
    """ Main function for running all helper functions and handling user input """
    # User entering their preferences
    print("Which scale?\n")
    scaleOptions = [scale for scale in scaleStructures.keys()]
    for i, option in enumerate(scaleOptions):
        print(f"{i+1}. {option.title()}?")
    key = input().lower()
    while key not in scaleStructures.keys():
        key = input("Invalid. Which scale?\n1. Major\n2. Minor\n").lower()

    root = input("Enter the root of your scale: ").lower()
    while root not in startingNotes.keys():
        root = input("Invalid. Enter the root of your scale: ").lower()

    tempo = input("Pick a tempo (integer) between 30 and 300 bpm: ")
    while not isValidTempo(tempo):
        tempo = input("Invalid. Pick a tempo (integer) between 30 and 300 bpm: ")
    tempo = int(tempo)

    scale = buildScale(root, key)

    populationSize = 10
    population = generatePopulation(populationSize, scale)
    #print([x for x in population if x is None or isinstance(x, int)])
    maxFitness = 10

    res = runEvolution(population, maxFitness, mutationRate, scale)

    for i in range(len(res)):
        writeMidiToDisk(res[i], f"out{i}.mid", tempo)

def buildScale(root, key):
    """ Builds scale based on passed in root and key by accessing pattern and starting note dictionaries """

    rootCode = startingNotes[root]
    scale = [rootCode]
    pattern = scaleStructures[key]
    currentCode = rootCode

    for i, j in enumerate(pattern):
        currentCode += j
        scale.append(currentCode)
    return [None] + scale

def generatePopulation(n, scale):
    """ Generate n 8 bar note sequences """
    population = [[[random.choice(scale) for x in range(16)] for y in range(8)] for z in range(n)]
    return population

def fitnessFunction(genome):
    """ Calculates fitness of a certain 8 bar sequence based on smoothness and rhythm """
    # Workaround to bug: will fix later
    if flatten(genome) == genome:
        return 0

    smoothnessScore = 0

    rhythmScore = 0

    harmonyScore = 0
    # Table that assigns different values to different intervals (in semitones). Higher valued intervals will be picked more
    harmonyWeightTable = {i: 10 * i for i in range(1,13)}

    numRests = genome.count(None)
    consecutiveRests = 0

    for i, bar in enumerate(genome):

        for j, note in enumerate(bar):

            # We can only determine smoothness in melody if we aren't at the first note of the genome AND the preceding note isn't a rest
            if j != 0 and note is not None and bar[j-1] is not None:
                prevNote = bar[j-1]
                # ABSOLUTE SMOOTHNEsS CALCULATION
                # Calculate how many semitones away this note is from the previous one
                noteDifference = abs(note - prevNote)
                # Penalize for repeating notes
                if not noteDifference:
                    smoothnessScore /= 10
                elif noteDifference <= 2:
                    smoothnessScore += 1

                # Penalize the major 7th interval
                elif noteDifference == 11:
                    smoothnessScore /= 2
                else:
                    if noteDifference != 0:
                        smoothnessScore += 1 / noteDifference

                # RELATIVE SMOOTHNESS CALCULATION
                # Relative pitch disregards the actual register of the note: if the notes are next to each other in the scale, then we can consider them being relaively smooth
                # This algorithm only deals with notes in a two octave range so thats all we need to consider
                if abs(note - (prevNote + 12)) == 1 or abs(note - (prevNote + 12)) == 2 or abs((note + 12) - prevNote) == 1 or abs((note + 12) - prevNote) == 2:
                    smoothnessScore += 0.5


            # Calculate number of consecutive rests there are
            if j != 0 and note is None and bar[j-1] is None:
                consecutiveRests += 1

    # Penalizes any sequences that have too many rests
    if numRests * 10 <= len(flatten(genome)):
        rhythmScore += 10

    # We don't want too many consecutive rests
    if consecutiveRests:
        rhythmScore /= consecutiveRests

    # Apply corresponding weights to scores in order to favour different characteristics
    fitness = (smoothnessScore * smoothnessWeight) + (rhythmScore * rhythmWeight)
    return fitness

def selectParents(population):
    """ Selects two 8 bar sequences from the population. Probability of being selected is weighted by the fitness score of each sequence """
    parentA, parentB = random.choices(population, weights=[fitnessFunction(genome) for genome in population], k=2)
    return parentA, parentB

def crossoverFunction(parentA, parentB):
    """ Performs single point crossover on two 8 bar sequences """
    # Merge each sequence into one contiguous string of notes by flattening the 2D array
    noteStringA = flatten(parentA)
    noteStringB = flatten(parentB)

    # Pick random position of sequence to use as the single point
    singlePoint = random.randint(1, len(parentA) - 1)
    # Perform crossover
    childAFlat = noteStringA[:singlePoint] + noteStringB[singlePoint:]
    childBFlat = noteStringB[:singlePoint] + noteStringA[singlePoint:]

    childA = []
    childB = []

    # Join the two children back into bars (A 2D array)
    barLength = len(parentA[0])
    sequenceLength = len(noteStringA)
    start = 0
    end = barLength
    while end <= sequenceLength:
        childA.append(childAFlat[start:end])
        childB.append(childBFlat[start:end])
        start = end
        end += barLength

    return childA, childB

def mutateGenome(genome, mutationRate, scale):
    """ Mutates an 8 bar sequence according to a mutation probability """
    for i, bar in enumerate(genome):
        for j, note in enumerate(bar):
            if random.uniform(0,1) <= mutationRate:
                # Two types of mutation can occur, either the note is flipped to a rest or it is transposed an octave lower. 50/50 chance of either mutation happening
                if random.uniform(0, 1) <= 0.5:
                #    genome[i][j] = None if note is not None else random.choice(scale)
            #    else:
                    genome[i][j] = note - 12 if note is not None else note

def runEvolution(population, maxFitness, mutationRate, scale):
    """ Runs genetic algorithm until a genome with the specified maxFitness score has been reached"""
    nextGeneration = []
    while True:

        population = sorted(population, key=lambda genome: [fitnessFunction(genome) for genome in population], reverse=True)
        if fitnessFunction(population[0]) >= maxFitness:
            break
        nextGeneration = population[0:2]
        for i in range(int(len(population) / 2) - 1):
            parentA, parentB = selectParents(population)
            childA, childB = crossoverFunction(parentA, parentB)
            mutateGenome(childA, mutationRate, scale)
            mutateGenome(childB, mutationRate, scale)
            nextGeneration += childA
            nextGeneration += childB
        population = nextGeneration

    population = sorted(population, key=lambda genome: [fitnessFunction(genome) for genome in population], reverse=True)
    return population

def writeMidiToDisk(sequence, filename="out", userTempo=60):
    """ Writes the generated sequence of numbers representing MIDI codes to a file with the specified filename """
    time = 0
    timeInterval = 0.25
    track = 0
    channel = 0
    tempo = userTempo
    duration = 0
    volume = 100

    midiFile = MIDIFile(1)
    midiFile.addTempo(track, time, tempo)
    fSequence = flatten(sequence)
    for pitch in fSequence:
        duration = random.choice([0.5, 0.75,1])
        if pitch is not None:
            midiFile.addNote(track, channel, pitch, time, duration, volume)
        timeInterval = random.choice([0.25, 0.5, 1])
        time += timeInterval

    with open(filename, "wb") as f:
        midiFile.writeFile(f)

def flatten(arr):
    """ Flattens a 2D array into a 1D array """
    res = []
    for i in arr:
        if isinstance(i, int) or i is None:
            return arr
        for j in i:
            res.append(j)
    return res

def isValidTempo(val):
    """ Returns True if the value is a valid tempo (is an integer and is between 30 and 300 (bpm)) """
    try:
        val = int(val)
    except:
        return False
    return val >= 30 and val <= 300

if __name__ == "__main__":
    main()
