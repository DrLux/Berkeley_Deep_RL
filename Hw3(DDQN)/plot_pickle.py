import pickle
import matplotlib.pyplot as plt

dict_file = open('picke_rewards.pkl', 'rb')           
rewards = pickle.load(dict_file)
dict_file.close()

episodes = list(range(0, len(rewards)))

plt.plot(episodes, rewards)
plt.ylabel('Rewards')
plt.xlabel('Episodes')
plt.savefig(str(len(episodes))+'.png')

