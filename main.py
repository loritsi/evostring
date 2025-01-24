from rapidfuzz import fuzz          # used to calculate string similarity
import random                       # used to generate random numbers
import time                         # used for timing
import matplotlib.pyplot as plt     # used for plotting the fitness graph

MAX_EVOSTRINGS = 250
# the maximum number of EvoStrings to keep in memory at any one time
# theoretically, if you set this to a really high number, the program could run out of memory and crash
# in practice, you could probably set this to a value in the tens of millions without any issues beyond being really slow
# you should probably keep this in the range of 50-5000 but you can experiment with it if you want
# if you set it below 4 the program will probably crash because we remove the bottom 25% of strings each generation

def get_closeness(string, goal):
    closeness = fuzz.ratio(string, goal)
    # if len(string) == len(goal):      # this is commented out because it caused the program to get stuck in a 
    #     closeness += 15               # situation where the string was the same length but not necessarily closer         
    return closeness                    # you can uncomment it if you're curious about that effect

def gen_string(min, max):
    genstring = []
    for i in range(random.randint(min, max)):           # generate a random string of random length between min and max
        genstring.append(chr(random.randint(32, 126)))  # here, we generate a random value between 32 and 126 and convert it to a character
    return ''.join(genstring)                           # 32-126 are printable utf-8 characters (i.e. letters, numbers, punctuation)   

def mutate_string(string, heat):
    # this function takes a string and basically jostles it around a bit to simulate the imperfections that would occur in nature
    # the heat parameter determines how much the string is jostled. the higher the heat, the more the string is changed
    # this combined with the fitness function gives us this dynamic:
    # 1) a bunch of random strings are generated
    # 2) we kill all the rubbish ones
    # 3) out of the remaining good ones, copy them and jostle them around a bit
    # 4) the random changes may be a bit worse or a bit better
    # 5) by killing the rubbish ones we're just left with the good ones again
    # we can repeat this process again and again, getting better and better strings each time, until we reach the goal
    # obviously, as the complexity of the goal increases, the number of generations required to reach it also increases
    # very complex goals may never be reached, but we can get pretty close with this method
    # the downside of using strings is that it doesn't work to just be "close enough", you have to be exactly right
    # evolutionary mechanisms in nature rarely require that kind of precision

    if heat < 0:            # if heat is negative
        heat = heat*-1      # make it positive by multiplying by -1
    
    if len(string) == 0:    # if the string is empty just send it back.
        return string       # there's no point in trying to mutate an empty string (it would probably just crash the program)
    
    if random.randint(0, 100) < 1:                  # 1% chance to completely change the string
        return gen_string(len(string), len(string)) # generate a completely new string of the same length

    numstring = bytes(string, 'utf-8')  # convert the string to a list of bytes (numbers) so we can modify it with random numbers

    newnumstring = []                   # create a list to put the bytes we're going to generate

    for i, byte in enumerate(numstring):

        modify_chance = random.randint(0, 100)  
        # instead of generating a random number for each if statement, we generate one here and use it multiple times. 
        # it's more efficient this way, and when we're generating potentially millions of random numbers 
        # per generation, efficiency is important

        if modify_chance < 50:                          # 10% chance to do nothing
            newbyte = byte                              # our "new byte" is the same as the old byte
        elif modify_chance < 75:                        # 25% chance to modify the character
            newbyte = byte + random.randint(-heat, heat)# our new byte is the old byte shifted over by a 
                                                        # random amount between heat and negative heat  
        else:                                           # 25% chance to completely change the character
            newbyte = random.randint(32, 126)           # our new byte is a completely random number between 32 and 126
        
        newbyte = max(32, newbyte)                      # make sure we don't go below 32 (the first printable character)
        newbyte = min(126, newbyte)                     # or above 126 (the last printable character)
        newnumstring.append(newbyte)                    # add our new byte to the list of all new bytes

    newstring = bytes(newnumstring).decode('utf-8')     # convert our list of new bytes back to a string

    add_remove_chance = random.randint(0, 100)          
    # again, generate a random number to use multiple times
    # we don't actually use it multiple times, but it allows us to add more conditions later if we want

    if add_remove_chance < 50:  # 50% chance to add or remove a character
        if random.choice([True, False]): # 50% chance to add a character
        # random doesn't have a random boolean function, 
        # so we use random.choice with a list of True and False
            insert_index = random.randint(0, len(newstring))
            # normally, we would use "len(newstring) - 1", but not doing that allows us to insert at the end of the string as well
            newstring = newstring[:insert_index] + chr(random.randint(32, 126)) + newstring[insert_index:]
        else:                   # 50% chance to remove a character
            remove_index = random.randint(0, len(newstring) - 1)                # pick a random index to remove
            newstring = newstring[:remove_index] + newstring[remove_index + 1:] # remove the character at that index

    return newstring    # at this point, newstring is already a string, so we don't need to convert it or anything
        
class EvoString:
    # why use a class here?

    # it's probably unnecessary, but it makes things like sorting and culling easier
    # when we sort the list of EvoStrings, we can just sort by the fitness attribute
    # and when we cull the list, we can just remove the EvoStrings with a lower fitness
    # this can be done with a list of tuples, but i think this is cleaner
    list = []       # list of all EvoStrings (this is a class variable, so it's shared between all instances)
    graveyard = 0   # amount of EvoStrings that have been killed (this is also a class variable)
    def __init__(self):                 # when we create a new EvoString
        self.string = gen_string(5, 20) # generate a random string
        self.fitness = None             # initialise the fitness value to None

    def makechild(self):
        # the makechild method is used to create a new EvoString from an existing one
        # 1) create a new EvoString like normal (it will have a random string at first)
        # 2) overwrite the string with a mutated version of the parent's string
        # 3) return the new EvoString (child) for use in the evolution process.
        # the script that calls this method is responsible for adding the child to the list of EvoStrings
        child = EvoString()
        child.string = mutate_string(self.string, 5)
        return child
    
    def kill(self):
        # instead of directly removing the EvoString from the list we use the kill method
        # this is not strictly necessary but it allows us to keep track of how many EvoStrings have been killed
        # we could also add more functionality here, like logging the string to a file or something
        EvoString.list.remove(self)
        EvoString.graveyard += 1
    
def sort_fitness(evolist, goal):
    # does what it says on the tin (sorts the list) but also returns all the fitness values so we can use them for statistics
    fitnesses = []
    for evostring in evolist:
        evostring.fitness = get_closeness(evostring.string, goal)
        fitnesses.append(evostring.fitness)
    evolist.sort(key=lambda x: x.fitness, reverse=True)
    return evolist, fitnesses

def cull_gradients(evolist):
    # this function removes EvoStrings with a lower fitness with a higher probability.
    # i.e. the lower the fitness, the higher the chance of being removed
    # a string in the top 10% of fitness has a 10% chance of being removed
    # a string in the bottom 20% of fitness has a 80% chance of being removed
    # strings in the bottom 10% are removed 100% of the time
    for i, evostring in enumerate(evolist):
        if i < 2: # keep the top 2 strings no matter what for stability
            continue
        chance = (i / len(evolist)) * 100   # calculate the chance of being removed (higher index = lower fitness)
        if random.randint(0, 100) < chance: # if the random number is less than the chance, kill the string
            evostring.kill()
        elif chance > 10:
            evostring.kill() # kill the bottom 25% of strings

    # truncated = evolist[:(MAX_EVOSTRINGS//4)] # get the bottom third of the list
    # for evostring in truncated:               # kill all the strings in the bottom third
    #     evostring.kill()

def reproduce(evolist):
    while len(evolist) < MAX_EVOSTRINGS:
        # recalculate weights dynamically based on the current list size
        weights = [len(evolist) - i for i in range(len(evolist))]
        
        random_parent = random.choices(evolist, weights=weights, k=1)[0]  # weighted random selection
        child = random_parent.makechild()  # create a child from the parent
        evolist.append(child)  # add the child to the list


def do_evolution(goal, max_gens=float('inf')):
    # the max_gens parameter is set to infinity by default, so the evolution will run until a string reaches the goal
    # if someone passes a number to max_gens, the evolution will run until that number of generations is reached
    # do_evolution("hello", max_gens=100) will run the evolution for 100 generations for example or if the goal is reached
    # do_evolution("hello") will just run the evolution forever until a string reaches the goal
    stats = {
        "avg_fitness": [],  # lists to store the average, max, min, and median fitness values for each generation
        "max_fitness": [],
        "min_fitness": [],
        "med_fitness": [],
    }


    EvoString.list = []         # reset the list of EvoStrings (it's prefixed with EvoString because it belongs to that class)
    EvoString.graveyard = 0     # reset the graveyard 
    for i in range(MAX_EVOSTRINGS):         # repeatedly create new EvoStrings until the list is full
        EvoString.list.append(EvoString())

    is_any_at_goal = False      # initialise a flag to check if any string has reached the goal
    generation = 0              # initialise the generation counter
    start = time.perf_counter() # start the timer to measure the time taken for each generation

    while not is_any_at_goal and generation < max_gens: 
    # run until a string reaches the goal or the max number of generations is reached
        generation += 1 # increment the generation counter (starting at 1)
        for evostring in EvoString.list:    # loop through all the EvoStrings
            if evostring.string == goal:    # if it has reached the goal, we're done!
                print("goal reached!")
                print(f"goal: {goal}\ntotal strings generated: {len(EvoString.list) + EvoString.graveyard}")
                print(f"generations: {generation}")
                is_any_at_goal = True       # set the flag to True so we can break out of the loop
            
        _, fitnesses = sort_fitness(EvoString.list, goal)
        avg_fitness = sum(fitnesses) / len(fitnesses)   # average fitness
        max_fitness = max(fitnesses)                    # max fitness
        min_fitness = min(fitnesses)                    # min fitness
        med_fitness = fitnesses[len(fitnesses) // 2]    # list is sorted, so the middle element is the median
        stats["avg_fitness"].append(avg_fitness)
        stats["max_fitness"].append(max_fitness)
        stats["min_fitness"].append(min_fitness)
        stats["med_fitness"].append(med_fitness)

        end = time.perf_counter()       # stop the timer (on the first run, this will not be accurate. but thats ok)

        elapsed = (end - start) * 1000  # convert the time to milliseconds

        padding = 20                    # padding for the print statement

        top5 = []
        for i in range(5):              # print the top 5 strings for each generation
            top5.append(f"({EvoString.list[i].fitness:.0f}) {EvoString.list[i].string:<{padding}}")

        top5 = ' '.join(top5)                  # join the top 5 strings into a single string
        print(f"{generation}: {top5}{elapsed:8.2f}ms")         # print the generation number and the top 5 strings

        #print(f"{generation:4d}: \t{EvoString.list[0].string:<{padding}} {EvoString.list[1].string:<{padding}} {EvoString.list[2].string:<{padding}} {EvoString.list[3].string:<{padding}} {EvoString.list[4].string:<{padding}} {elapsed:8.2f}ms")
        
        # what is going on here?
        # we're printing the generation number, the top 5 strings, and the time taken for that generation
        # the weird syntax allows us to format the strings so they always take up the same amount of space
        # otherwise, the output is really hard to read. replace that string with the one below to see what i mean

        # print(f{generation}: {EvoString.list[0].string} {EvoString.list[1].string} {EvoString.list[2].string} {EvoString.list[3].string} {EvoString.list[4].string} {elapsed:.2f}ms)

        # here is how the formatting works:
        # {variable:width} where variable is the variable you want to print and width is the width you want it to take up
        # the "<" symbol means left-align the string, and we pass the padding variable as the width, so we can change it easily

        # also, we use elapsed:.2f to round the time to 2 decimal places
        # :8.2f means "take up 8 spaces and round to 2 decimal places"
        # by default, the number will be right-aligned, so we don't need to specify that, but we could if we wanted to by using ">"

        start = time.perf_counter()     # start the timer for the next generation
        cull_gradients(EvoString.list)  # remove strings with a lower fitness
        reproduce(EvoString.list)       # create children from the remaining strings
    return stats    # once we're completely done, return the stats

                
while True:
    plt.clf() # clear the plot
    goal = input("enter a goal string: ")   # we use input() to get a string from the user
    stats = do_evolution(goal)              # run the evolution with the goal string, and assign the stats to a variable
    avgf, maxf, minf, medf = stats["avg_fitness"], stats["max_fitness"], stats["min_fitness"], stats["med_fitness"]
    # unpack the stats into separate lists for plotting
    timeaxis = list(range(len(avgf))) 
    # create a list of numbers from 0 to the length of the average fitness list
    # this will be our x-axis for the plot (generation number)

    plt.plot(timeaxis, avgf, label="average fitness")   # use matplotlib to plot the fitness values
    plt.plot(timeaxis, maxf, label="max fitness")
    plt.plot(timeaxis, minf, label="min fitness")
    plt.plot(timeaxis, medf, label="median fitness")
    plt.xlabel("generation")    # add labels to the plot
    plt.ylabel("fitness")
    plt.legend()                # show the legend
    plt.show()                  # open the plot as a window

    input("press enter to continue")    # wait until the user presses enter before asking for a new goal string