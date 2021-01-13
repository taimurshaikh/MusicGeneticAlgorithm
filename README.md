# MusicGeneticAlgorithm
This program generates a set of melodies based on the key that the user inputs. The melodies are evolved using a genetic algorithm for a specified number of generations. The fitness function of the genetic algorithm currently takes into account melodic smoothness and rhythm. The program outputs the melodies as MIDI files in the same directory as the genetic.py script
#Usage
Run the program with F5. The terminal will then ask for the desired scale, root and tempo of your output melodies. The program will then output the MIDI files in your directory. The POPULATION_SIZE variable controls how many files will be generated. Additionally, you can adjust MUTATION_RATE to affect how often the notes in the files will be randomly changed. 
