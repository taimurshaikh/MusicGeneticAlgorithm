""" Genetic Algorithm for music generation. Takes a user defined key and tempo and evolves a melody according to those """
import random
from midiutil import MIDIFile

POPULATION_SIZE = 10
MAX_GENERATIONS = 100
MUTATION_RATE = 0.1
MAX_FITNESS = 30
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

smoothnessWeight = 15
rhythmWeight = 15
harmonyWeight = 15


def main():
    """ Main function for running all helper functions and handling user input """
    # User entering their preferences
    print("Which scale?")

    scaleOptions = [scale for scale in scaleStructures.keys()]

    for i, option in enumerate(scaleOptions):
        print(f"{i+1}. {option.title()}?")
    key = input(" ").lower().strip()

    while key not in scaleStructures.keys():
        print("Invalid.")
        for i, option in enumerate(scaleOptions):
            print(f"{i+1}. {option.title()}?")
        key = input().lower().strip()

    root = input("Enter the root of your scale: ").lower().strip()
    while root not in startingNotes.keys():
        root = input("Invalid. Enter the root of your scale: ").lower().strip()

    tempo = input("Pick a tempo (integer) between 30 and 300 bpm: ").strip()
    while not isValidTempo(tempo):
        tempo = input("Invalid. Pick a tempo (integer) between 30 and 300 bpm: ").strip()
    tempo = int(tempo)

    scale = buildScale(root, key)
    res = runEvolution(MUTATION_RATE, scale)

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

def generateGenome(scale):
    """ Generates one note sequence """
    return [[random.choice(scale) for x in range(16)] for y in range(8)]

def generatePopulation(n, scale):
    """ Generate n note sequences """
    population = [generateGenome(scale) for x in range(n)]
    return population

def fitnessFunction(genome):
    """ Calculates fitness of a certain sequence based on smoothness and rhythm """

    # Workaround to really difficult to solve bug: will fix when I find what's causing it
    if flatten(genome) == genome or genome is None:
         return 0

    smoothnessScore = 0

    rhythmScore = 0

    harmonyScore = 0
    # Table that assigns different values to different intervals (in semitones). Higher valued intervals will be picked more. Currently the 3rd and 5th are valued the highest, and penalizes repeated notes, tritones and sevenths
    harmonyIntervalsTable = {0 : -20, 1 : 5, 2 : 5, 3 : 50, 4 : 50, 5 : 30, 6 : -10, 7 : 50, 8 : 10, 9 : 40, 10 : -2, 11 : -2, 12 : 10,
                             13 : -5, 14 : 5, 15 : 5, 16 : 50, 17 : 50, 18 : 30, 19 : -10, 20 : 50, 21 : 10, 22 : 40, 23 : -2, 24 : -2, 25 : 10}

    numRests = genome.count(None)
    consecutiveRests = 0

    for i, bar in enumerate(genome):

        for j, note in enumerate(bar):

            # We can only determine smoothness in melody if we aren't at the first note of the genome AND the preceding note isn't a rest
            if j != 0 and note is not None and bar[j-1] is not None:
                prevNote = bar[j-1]
                # ABSOLUTE SMOOTHNESS CALCULATION
                # Calculate how many semitones away this note is from the previous one
                noteDifference = abs(note - prevNote)

                # Add corresponding harmony score based on interval
                harmonyScore += harmonyIntervalsTable[noteDifference]

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

    penalty = 10
    # We don't want too many consecutive rests
    if consecutiveRests:
        rhythmScore -= (consecutiveRests * penalty)

    # Apply corresponding weights to scores in order to favour different characteristics
    fitness = (smoothnessScore * smoothnessWeight) + (rhythmScore * rhythmWeight)
    return fitness

def selectParents(population):
    """ Selects two sequences from the population. Probability of being selected is weighted by the fitness score of each sequence """
    parentA, parentB = random.choices(population, weights=[fitnessFunction(genome) for genome in population], k=2)
    return parentA, parentB

def crossoverFunction(parentA, parentB):
    """ Performs single point crossover on two sequences """
    # Merge each sequence into one contiguous string of notes by flattening the 2D array
    noteStringA = flatten(parentA)
    noteStringB = flatten(parentB)

    if len(noteStringA) != len(noteStringB):
        print("INVALID BRO")
        raise ValueError
    elif len(parentA) < 2:
        print('A small bro')
        return parentA, parentB

    # Pick random position of sequence to use as the single point
    singlePoint = random.randint(1, len(noteStringA) - 1)
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
    """ Mutates an  sequence according to a mutation probability """
    for i, bar in enumerate(genome):
        for j, note in enumerate(bar):
            if random.uniform(0,1) <= mutationRate:
                    genome[i][j] = None if note is not None else random.choice(scale)
    return genome

def runEvolution(mutationRate, scale):
    """ Runs genetic algorithm until a genome with the specified MAX_FITNESS score has been reached"""

    population = generatePopulation(POPULATION_SIZE, scale)

    nextGeneration = []
    generations = 0
    for i in range(MAX_GENERATIONS):

        population = sorted(population, key=lambda genome: fitnessFunction(genome), reverse=True)

        nextGeneration = population[0:2]

        for j in range(int(len(population) / 2) - 1):
            parentA, parentB = selectParents(population)
            childA, childB = crossoverFunction(parentA, parentB)

            childA = mutateGenome(childA, mutationRate, scale)
            childB = mutateGenome(childB, mutationRate, scale)

            nextGeneration += [childA, childB]

        population = nextGeneration
        generations += 1

    population = sorted(population, key=lambda genome: fitnessFunction(genome), reverse=True)
    print(generations)
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
        duration = random.choice([0.5, 0.75, 1])
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
