<template>
  <div id="app">
    <h1>Bind Your Function Keys</h1>
    <div class="function-keys">
      <div v-for="(binding, functionName) in bindings" :key="functionName" class="function-key">
        <button class="delete-button" @click="deleteBinding(functionName)">×</button>
        <div :class="['function-name', {'missing-device': !binding.deviceFound}]">{{ functionName }}:</div>
        <div class="function-binding" :style="{ color: bindingFunction === functionName ? 'red' : 'black' }">
          {{ bindingFunction === functionName ? 'Please press a key...' : binding.displayKey }}
        </div>
        <button class="bind-button" @click="startBinding(functionName)" :disabled="isRunning">Bind</button>
      </div>
    </div>
    <button class="start-button" @click="start" :disabled="isRunning">Start</button>
    <button class="stop-button" @click="stop" :disabled="!isRunning">Stop</button>
    <button class="clear-button" @click="clearBindings">Clear All Bindings</button>
    <div class="status-bar">{{ status }}</div>
    <div class="log">
      <div class="log-content">
        <ul>
          <li v-for="log in logs" :key="log.timestamp">{{ log.timestamp }} - {{ log.function }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { io } from 'socket.io-client';
import {reactive, ref, onMounted} from 'vue';
import './styles.css';

export default {
  setup() {
    const bindings = reactive({
      'Trim Set': { displayKey: 'Not bound', deviceFound: true },
      'Trim Release': { displayKey: 'Not bound', deviceFound: true },
      'Trim Left': { displayKey: 'Not bound', deviceFound: true },
      'Trim Right': { displayKey: 'Not bound', deviceFound: true }
    });

    const bindingFunction = ref(null);
    const socket = io('http://localhost:5000');
    const status = ref('Idle');
    const isRunning = ref(false);
    const logs = ref([]);


    const startBinding = (functionName) => {
      bindingFunction.value = functionName;
      axios.post('http://localhost:5000/bind', {
        function: functionName
      }).then(() => {
        // Add event listener for single use
        const handleBindingsUpdated = (updatedBindings) => {
          for (const fn in updatedBindings) {
            updateBindingDisplay(fn, updatedBindings[fn]);
          }
          bindingFunction.value = null;  // Reset binding function
          socket.off('bindings_updated', handleBindingsUpdated);  // Remove event listener after update
        };
        socket.on('bindings_updated', handleBindingsUpdated);
      });
    };

    const updateBindingDisplay = (functionName, event) => {
      bindings[functionName].displayKey = event.button !== null
          ? `${event.device_name} Button ${event.button}`
          : `${event.device_name} POV ${event.pov}`;
      bindings[functionName].deviceFound = true;
    };

    const loadBindings = () => {
      axios.get('http://localhost:5000/bindings')
          .then(response => {
            const serverBindings = response.data;
            for (const functionName in serverBindings) {
              const event = serverBindings[functionName];
              updateBindingDisplay(functionName, event);
              if (event.device_id === null) {
                bindings[functionName].deviceFound = false;
              }
            }
          });
    };

    const clearBindings = () => {
      axios.post('http://localhost:5000/clear_bindings')
          .then(() => {
            for (const functionName in bindings) {
              bindings[functionName].displayKey = 'Not bound';
              bindings[functionName].deviceFound = true;
            }
          });
    };

    const deleteBinding = (functionName) => {
      axios.post('http://localhost:5000/delete', {
        function: functionName,
      }).then(() => {
        loadBindings();
      });
    };

    const start = () => {
      axios.post('http://localhost:5000/start')
          .then((response) => {
            if (response.data.success) {
              isRunning.value = true;
              updateStatus();
            } else {
              alert(response.data.message);
            }
          });
    };

    const stop = () => {
      axios.post('http://localhost:5000/stop')
          .then((response) => {
            if (!response.data.success) {
              alert(response.data.message);
            }
            isRunning.value = false;
            updateStatus();
          });
    };

    const updateStatus = () => {
      axios.get('http://localhost:5000/status')
          .then(response => {
            status.value = response.data.status;
          });
    };

    const addLog = (func) => {
      const timestamp = new Date().toLocaleString();
      logs.value.unshift({ timestamp, function: func });
    };

    socket.on('log', (func) => {
      addLog(func);
    });

    socket.on('bindings_updated', (updatedBindings) => {
      for (const functionName in updatedBindings) {
        updateBindingDisplay(functionName, updatedBindings[functionName]);
      }

      // 清除没有更新的绑定
      for (const functionName in bindings) {
        if (!updatedBindings[functionName]) {
          bindings[functionName].displayKey = 'Not bound';
          bindings[functionName].deviceFound = true;
        }
      }
    });

    onMounted(() => {
      loadBindings();
      updateStatus();
    });

    return {
      bindings,
      startBinding,
      clearBindings,
      deleteBinding,
      start,
      stop,
      status,
      isRunning,
      bindingFunction,
      logs
    };
  }
};
</script>

<style>
/* Add your styles here */
</style>
