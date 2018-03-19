{% load staticfiles %}
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>django-carrot monitor</title>
    <link href='https://fonts.googleapis.com/css?family=Roboto:300,400,500,700|Material+Icons' rel="stylesheet" type="text/css">
    <link href="https://unpkg.com/vuetify/dist/vuetify.min.css" rel="stylesheet" type="text/css">
    <!--<link rel="icon" type="image/png" href="favicon-32x32.png" sizes="32x32">-->
</head>
<body>
  <div id="app">
    <v-app>
      <v-toolbar fixed app dark tabs color="orange darken-2">
        <v-spacer></v-spacer>
        <v-avatar size="34" tile>
            <img src="{% static 'carrot/white-carrot.png' %}">
        </v-avatar>
        <v-toolbar-title v-text="title" class="display-1"></v-toolbar-title>
        <v-spacer></v-spacer>
        <v-tabs
          centered
          color="orange darken-2"
          slot="extension"
          slider-color="yellow"
          v-model="tabs"
        >
          <v-tab
            v-for="page in pages"
            :key="page.id"
            :href="`#tab-${page.id}`"
          >
            [{ page.title }]
          </v-tab>
        </v-tabs>
      </v-toolbar>
      <v-content>
          <v-dialog
            v-model="displayMessageLog"
            max-width="800px"
            transition="dialog-bottom-transition"
            :overlay="false"
            persistent
          >
              <v-card tile v-if="selectedMessageLog">
                  <v-toolbar dark :class="getColor()">
                      <v-toolbar-title>[{ selectedMessageLog.task }]
                      </v-toolbar-title>
                      <v-spacer></v-spacer>
                      <v-btn icon @click.native="displayMessageLog = false" dark>
                          <v-icon>close</v-icon>
                      </v-btn>
                  </v-toolbar>
                  <v-subheader>Basic information</v-subheader>
                  <v-divider></v-divider>

                  <v-list>
                      <v-list-tile>
                          <v-list-tile-content>Virtual host</v-list-tile-content>
                          <v-list-tile-content class="align-end">[{ selectedMessageLog.virtual_host }]</v-list-tile-content>
                      </v-list-tile>
                      <v-list-tile>
                          <v-list-tile-content>Queue</v-list-tile-content>
                          <v-list-tile-content class="align-end">[{ selectedMessageLog.queue || 'default' }]</v-list-tile-content>
                      </v-list-tile>
                      <v-list-tile>
                          <v-list-tile-content>Status</v-list-tile-content>
                          <v-list-tile-content class="align-end">[{ selectedMessageLog.status }]</v-list-tile-content>
                      </v-list-tile>
                      <v-list-tile>
                          <v-list-tile-content>Priority</v-list-tile-content>
                          <v-list-tile-content class="align-end">[{ selectedMessageLog.priority }]</v-list-tile-content>
                      </v-list-tile>
                      <v-list-tile>
                          <v-list-tile-content>Publish time</v-list-tile-content>
                          <v-list-tile-content class="align-end">[{ selectedMessageLog.publish_time | displayTime }]</v-list-tile-content>
                      </v-list-tile>
                  </v-list>
                  <v-subheader>Task arguments</v-subheader>
                  <v-divider></v-divider>
                  <v-list>
                      <v-list-tile>
                          <v-list-tile-content>Positional arguments</v-list-tile-content>
                          <v-list-tile-content class="align-end">[{ selectedMessageLog.task_args }]</v-list-tile-content>
                      </v-list-tile>
                      <v-list-tile v-for="item in parsed(selectedMessageLog.content)" :key="item.key">
                          <v-list-tile-content>[{ item.key }]</v-list-tile-content>
                          <v-list-tile-content class="align-end">[{ item.val }]</v-list-tile-content>
                      </v-list-tile>
                  </v-list>
                  <div v-if="selectedMessageLog.log">
                      <v-subheader>Task log</v-subheader>
                      <v-divider></v-divider>
                      <v-container>
                          <v-select
                              :items="levels"
                              v-model="logLevel"
                              label="Level"
                              item-text="label"
                              item-value="value"
                          ></v-select>

                        <v-layout row wrap>
                            <v-flex xs12 v-if="display(line)" v-for="line in split(selectedMessageLog.log)">
                                <v-card :class="getClass(line.logLevel)">
                                    <v-card-title>
                                        <v-icon>[{ getIcon(line.logLevel) }]</v-icon>
                                        <span class="subheader">[{ line.time | displayTime }]</span>
                                        <strong v-if="line.logLevel === 5">[{ line.message }]</strong>
                                        <span v-else>[{ line.message}]</span>
                                    </v-card-title>
                                </v-card>
                            </v-flex>
                        </v-layout>
                    </v-container>
                  </div>
                  <div v-if="selectedMessageLog.status === 'FAILED'">
                      <v-subheader>Traceback</v-subheader>
                      <v-divider></v-divider>
                      <v-container grid-list-md text-xs-left>
                          <v-layout row wrap>
                              <v-flex xs12>
                                  <v-card class="error--text red lighten-4">
                                        <v-card-title>
                                            <v-container>
                                                <v-layout row wrap>
                                                     <v-flex :class="getTracebackOffset(line)" v-for="(line, index) in selectedMessageLog.traceback.split('\n')" :key="index">
                                                       <font face="Monospace">[{ line }]</font>
                                                     </v-flex>
                                                </v-layout>
                                            </v-container>
                                         </v-card-title>
                                  </v-card>
                              </v-flex>
                          </v-layout>
                      </v-container>
                  </div>
                  <v-card-actions v-if="selectedMessageLog.status === 'FAILED'">
                      <v-spacer></v-spacer>
                      <v-btn flat text class="error" @click="deleteOne"><v-icon left>close</v-icon>Delete</v-btn>
                      <v-btn flat text class="blue" @click="requeueOne"><v-icon left>cached</v-icon>Requeue</v-btn>
                  </v-card-actions>
              </v-card>

          </v-dialog>
          <v-dialog
            persistent
            v-model="displayScheduledTask"
            max-width="800px"
            transition="dialog-bottom-transition"
          >
              <v-card v-if="selectedScheduledTask">
                  <v-toolbar dark class="white--text" dense :color="getColor()">

                      <v-toolbar-title v-if="selectedScheduledTask.id">[{ selectedScheduledTask.task }]</v-toolbar-title>
                      <v-toolbar-title v-else>Create new scheduled task</v-toolbar-title>
                      <v-spacer></v-spacer>
                      <v-btn icon @click.native="displayScheduledTask = false" dark>
                          <v-icon>close</v-icon>
                      </v-btn>
                  </v-toolbar>
                <v-form v-model="valid">
                  <v-container grid-list-md>
                      <v-layout row wrap>
                          <v-flex xs12>
                              <v-select
                                      v-model="selectedScheduledTask.task"
                                      :items="taskChoices"
                                      label="task"
                                      required
                                      autocomplete
                              >
                              </v-select>
                          </v-flex>

                          <v-flex xs6>
                              <v-text-field
                                      multi-line
                                      value="taskArgs"
                                      label="Positional arguments"
                                      @change="revalidate"
                                      :error-messages="positionalErrors"
                                      v-model="selectedScheduledTask.task_args"
                              ></v-text-field>
                          </v-flex>
                          <v-flex xs6>
                              <v-text-field
                                      multi-line
                                      label="Keyword arguments"
                                      :rules="validKeywords"
                                      v-model="selectedScheduledTask.content"
                              ></v-text-field>
                          </v-flex>
                            <v-flex xs4>
                              <v-text-field
                                      label="Queue"
                                      required
                                      :rules="required"
                                      v-model="selectedScheduledTask.queue"
                              ></v-text-field>
                          </v-flex>
                          <v-flex xs4>
                              <v-text-field
                                      label="Exchange"
                                      v-model="selectedScheduledTask.exchange"
                              ></v-text-field>
                          </v-flex>
                          <v-flex xs4>
                              <v-text-field
                                      label="Routing key"
                                      v-model="selectedScheduledTask.routing_key"
                              ></v-text-field>
                          </v-flex>

                          <v-flex xs4>
                              <v-text-field
                                      prepend-icon="access_time"
                                      label="Every"
                                      label="Interval count"
                                      :rules="requiredNumeric"
                                      required
                                      v-model="selectedScheduledTask.interval_count"
                          ></v-text-field>
                          </v-flex>
                          <v-flex xs4>
                               <v-select
                                  single-line
                                  label="Interval type"
                                  :items="intervalTypes"
                                  :rules="required"
                                  v-model="selectedScheduledTask.interval_type"
                                  required
                          ></v-select>
                          </v-flex>
                          <v-flex xs4></v-flex>
                          <v-flex xs4 align-end>
                            <v-switch
                                  label="Active"
                                  v-model="selectedScheduledTask.active"
                              ></v-switch>
                          </v-flex>

                      </v-layout>
                  </v-container>
                </v-form>
                  <v-card-actions>
                      <v-spacer></v-spacer>
                      <v-btn text flat class="error" @click="deleteScheduledTask" :disabled="!selectedScheduledTask.id">Delete</v-btn>
                      <v-btn text flat class="primary--text" @click="saveScheduledTask" :disabled="!valid" :loading="loading">Save changes</v-btn>
                      <v-btn text flat class="primary--text" @click="runScheduledTask" :disabled="!selectedScheduledTask.id">Run now</v-btn>
                  </v-card-actions>
              </v-card>
          </v-dialog>

        <v-container fluid>
          <v-tabs-items v-model="tabs">
            <v-tab-item
              v-for="page in pages"
              :key="page.id"
              :id="'tab-' + page.id"
            >
              <v-card>
                <v-toolbar dark class="white--text" dense :color="getColor()">
                  <v-toolbar-title>[{ page.title }] tasks</v-toolbar-title>
                </v-toolbar>
                <v-card-title v-if="tabs !== 'tab-scheduled'">
                  Search
                  <v-spacer></v-spacer>
                  <v-text-field
                    append-icon="search"
                    label="Search"
                    single-line
                    hide-details
                    v-model="search"
                  ></v-text-field>
                </v-card-title>
                <v-data-table
                    :headers="getHeaders()"
                    :items="tasks"
                    :pagination.sync="pagination"
                    :total-items="totalItems"
                    :rows-per-page-items="[50]"
                >
                  <template slot="items" slot-scope="props" >
                      <tr v-if="tabs === 'tab-published'" @click.stop="selectedMessageLog = props.item">
                        <td>[{ props.item.priority }]</td>
                        <td>[{ props.item.task }]</td>
                        <td>[{ props.item.task_args }]</td>
                        <td>[{ props.item.content }]</td>
                      </tr>
                      <tr v-else-if="tabs === 'tab-failed'" @click.stop="selectedMessageLog = props.item">
                        <td>[{ props.item.failure_time | displayTime }]</td>
                        <td>[{ props.item.task }]</td>
                        <td>[{ props.item.task_args }]</td>
                        <td>[{ props.item.content }]</td>
                        <td>[{ props.item.exception }]</td>
                      </tr>
                      <tr v-else-if="tabs === 'tab-completed'" @click.stop="selectedMessageLog = props.item">
                        <td>[{ props.item.completion_time | displayTime }]</td>
                        <td>[{ props.item.task }]</td>
                        <td>[{ props.item.task_args }]</td>
                        <td>[{ props.item.content | cropped }]</td>
                      </tr>
                      <tr v-else @click="selectedScheduledTask = props.item">
                          <td>[{ props.item.task }]</td>
                          <td>Every [{ props.item.interval_count }] [{ props.item.interval_type }]</td>
                          <td><v-icon v-if="props.item.active">check</v-icon><v-icon v-else>close</v-icon></td>
                      </tr>
                  </template>
                </v-data-table>
                  <v-card-actions v-if="tabs === 'tab-failed'">
                      <v-spacer></v-spacer>
                      <v-btn flat text class="error" @click="deleteAll"><v-icon left>close</v-icon>Delete all</v-btn>
                      <v-btn flat text class="blue" @click="requeueAll"><v-icon left>cached</v-icon>Requeue all</v-btn>
                  </v-card-actions>
                  <v-card-actions v-if="tabs === 'tab-scheduled'">
                      <v-spacer></v-spacer>
                      <v-btn flat text class="blue" @click="createNew"><v-icon left>add</v-icon>Create new</v-btn>
                  </v-card-actions>
              </v-card>
            </v-tab-item>
          </v-tabs-items>
        </v-container>
      </v-content>
    </v-app>
  </div>

  <script src="https://unpkg.com/vue/dist/vue.min.js"></script>
  <script src="https://unpkg.com/vuetify/dist/vuetify.min.js"></script>
  <script src="https://unpkg.com/vuex"></script>
  <script src="https://cdn.jsdelivr.net/npm/lodash@4.17.5/lodash.min.js"></script>
  <script src="https://unpkg.com/axios/dist/axios.min.js"></script>
  <script type="text/javascript">
    const store = new Vuex.Store({
      state: {
        tasks: [],
        totalItems: 0,
        taskChoices: [],
      },
      mutations: {
        SET_TASKS: function (state, messageLogs) {
            state.tasks = messageLogs
        },
        SET_COUNT: function (state, count) {
          state.totalItems = count
        },
        SET_TASK_CHOICES: function (state, choices) {
          state.taskChoices = choices
        }
      },
      actions: {
        async getTasks ({ commit }, { page, type, search, scheduled }) {
            if (scheduled) {
              var url = '/carrot/api/scheduled-tasks/?page=' + page
            } else {
              var url = '/carrot/api/message-logs/' + type + '/?page=' + page
            }

            if (search) {
              var url = url + '&search=' + search
            }
            let { data } = await axios.get(url)
            commit('SET_COUNT', data.count)
            commit('SET_TASKS', data.results)
        },
        async getTaskChoices({ commit }) {
            var { data } = await axios.get('/carrot/api/scheduled-tasks/task-choices/')
            commit('SET_TASK_CHOICES', data)
        },
        async deleteOne ({ commit }, id ) {
            await axios.delete('/carrot/api/message-logs/' + id + '/',
                {
                    headers: {
                        'X-CSRFToken': '{{ csrf_token }}'
                    }
                }
            )
        },
        async requeueOne ({ commit }, id ) {
            await axios.put('/carrot/api/message-logs/' + id + '/', {},
                {
                    headers: {
                        'X-CSRFToken': '{{ csrf_token }}'
                    }
                }
            )
        },
        async deleteAll ({ commit }) {
            await axios.delete('/carrot/api/message-logs/failed/',
                {
                    headers: {
                        'X-CSRFToken': '{{ csrf_token }}'
                    }
                }
            )
        },
        async requeueAll ({ commit } ) {
            await axios.put('/carrot/api/message-logs/failed/', {},
                {
                    headers: {
                        'X-CSRFToken': '{{ csrf_token }}'
                    }
                }
            )
        },
        deleteScheduledTask ({ commit }, taskId) {
            axios.delete('/carrot/api/scheduled-tasks/' + taskId + '/',
                {
                    headers: {
                        'X-CSRFToken': '{{ csrf_token }}'
                    }
                }
            )
        },
        async saveScheduledTask ({ commit }, task) {
            await axios.patch('/carrot/api/scheduled-tasks/' + task.id + '/', task,
                {
                    headers: {
                        'X-CSRFToken': '{{ csrf_token }}'
                    }
                }
            )
        },
        runScheduledTask ({ commit }, taskId ) {
            axios.get('/carrot/api/scheduled-tasks/' + taskId + '/run/',
                {
                    headers: {
                        'X-CSRFToken': '{{ csrf_token }}'
                    }
                }
            )
        },
        async createScheduledTask ({ commit }, task) {
            try {
                await axios.post('/carrot/api/scheduled-tasks/', task,
                    {
                        headers: {
                            'X-CSRFToken': '{{ csrf_token }}'
                        }
                    }
                )
            } catch (error) {
                console.error(error)
            }
        }
      },

    })

    new Vue({
      delimiters: ['[{', '}]'],
      store,
      el: '#app',
      created () {
        var self = this
        setInterval(
            function () {
                if (self.tabs !== 'tab-scheduled') {
                    self.updateTasks()
                }
            },
        10000)
        this.$store.dispatch('getTaskChoices')

        this.$vuetify.theme = {
          primary: '#fb8c00',
          secondary: '#90a4ae',
          error: '#FF5252',
          info: '#2196F3',
          success: '#4CAF50',
          warning: '#FFC107'
        }
      },
      filters: {
        cropped (value) {
            if (String(value).length > 1000) {
                value = String(value).slice(0, 1000) + '...'
            }
            return value
        },
        displayTime (time) {
            return new Date(time).toLocaleString()
        }
      },
      watch: {
         selectedMessageLog () {
            if (this.selectedMessageLog) {
                this.displayMessageLog = true
            }
        },
        displayMessageLog () {
            if (!this.displayMessageLog) {
                this.selectedMessageLog = null
            }
        },
        selectedScheduledTask () {
            if (this.selectedScheduledTask) {
                this.displayScheduledTask = true
            }
        },
        displayScheduledTask () {
            if (!this.displayScheduledTask) {
                this.selectedScheduledTask = null
            }
        },
        tabs () {
          this.pageNumber = 1
          this.search = null
          this.updateTasks()
        },
        pagination () {
          this.pageNumber = this.pagination.page
        },
        pageNumber () {
          this.updateTasks()
        },
        search: _.debounce(function() {
           this.pageNumber = 1
           this.updateTasks()
        }, 500)
      },
      computed: {
        tasks () {
          return this.$store.state.tasks
        },
        totalItems () {
          return this.$store.state.totalItems
        },
        taskChoices () {
            return this.$store.state.taskChoices
        }
      },
      methods: {
        getTracebackOffset (line) {
            var offset = line.search(/\S|$/) / 2
            var width = 12 - offset
            return 'xs' + width + ' offset-xs' + offset
        },
        createNew () {
            this.selectedScheduledTask = {
                id: null,
                task: null,
                task_args: null,
                content: null,
                queue: null,
                exchange: null,
                routing_key: null,
                interval_count: null,
                interval_type: null,
                active: false
            }
        },
        async revalidate (val) {
            var { data } = await axios.post('/carrot/api/scheduled-tasks/validate-args/', { args: val },
                 {
                    headers: {
                        'X-CSRFToken': '{{ csrf_token }}'
                    }
                }
            )
            this.positionalErrors = data.errors
        },
        async deleteScheduledTask () {
            await this.$store.dispatch('deleteScheduledTask', this.selectedScheduledTask.id)
            this.updateTasks()
            this.displayScheduledTask = false
        },
        runScheduledTask () {
            this.$store.dispatch('runScheduledTask', this.selectedScheduledTask.id)
            this.updateTasks()
            this.displayScheduledTask = false
        },
        async saveScheduledTask () {
            this.loading = true
            if (this.selectedScheduledTask.id) {
                await this.$store.dispatch('saveScheduledTask', this.selectedScheduledTask)
                this.updateTasks()
                this.displayScheduledTask = false
            } else {
                await this.$store.dispatch('createScheduledTask', this.selectedScheduledTask)
                this.updateTasks()
                this.displayScheduledTask = false
            }
            this.loading = false
        },
        async requeueOne () {
            await this.$store.dispatch('requeueOne', this.selectedMessageLog.id)
            await this.updateTasks()
            this.selectedMessageLog = null
            this.displayMessageLog = false
        },
        async deleteOne () {
            await this.$store.dispatch('deleteOne', this.selectedMessageLog.id)
            await this.updateTasks()
            this.selectedMessageLog = null
            this.displayMessageLog = false
        },
        async requeueAll () {
            await this.$store.dispatch('requeueAll')
            await this.updateTasks()
        },
        async deleteAll () {
            await this.$store.dispatch('deleteAll')
            await this.updateTasks()
        },
        display (line) {
            if (line.logLevel >= this.logLevel) {
                return true
            }
        },
        getClass (logLevel) {
          if (logLevel === 1) {
            return 'grey lighten-2'
          } else if (logLevel === 2) {
            return 'success--text green lighten-4'
          } else if (logLevel === 3) {
            return 'warning--text amber lighten-4'
          } else {
            return 'error--text red lighten-4'
          }
        },
        getIcon (logLevel) {
          if (logLevel === 1) {
            return 'code'
          } else if (logLevel === 2) {
            return 'info_outline'
          } else if (logLevel === 3) {
            return 'warning'
          } else {
            return 'error_outline'
          }
        },
        split (lines) {
            var splitLines = lines.split('\n')
            var levels = {
                DEBUG: 1,
                INFO: 2,
                WARNING: 3,
                ERROR: 4,
                CRITICAL: 5
            }
            var output = []
            for (var l in splitLines) {
                var line = splitLines[l]
                if (line) {
                    var message = line.slice(line.indexOf('::')+3, 100000)
                    var pre = line.split('::')[0].split(' ')
                    var consumer = pre[0]
                    var levelName = pre.slice(-1)[0]
                    var time = pre.slice(1, 3).join('T').split(',')[0]
                    var logLevel = levels[levelName]
                    var lineData = {
                        message, consumer, levelName, time, consumer, logLevel
                    }
                    output.push(lineData)
                }
            }
            return output
        },
        parsed (content) {
            var output = []
            var obj =  JSON.parse(content)
            for (var key in obj) {
                var val = String(obj[key])
                if (val.length > 50) {
                    val = val.slice(0, 50) + '...'
                }
                output.push({
                    key, val
                })
            }
            return output
        },
        updateTasks () {
          var type = this.tabs.replace('tab-','')
          this.$store.dispatch('getTasks', {
            page: this.pageNumber,
            type,
            search: this.search,
            scheduled: this.tabs === 'tab-scheduled'
          })
        },
        getColor () {
          if (this.tabs === 'tab-published') {
           return 'orange darken-2'
          } else if (this.tabs === 'tab-failed') {
           return 'error'
          } else if (this.tabs === 'tab-completed') {
           return 'success'
          } else {
            return 'blue-grey lighten-1'
          }

        },
        getHeaders () {
          if (this.tabs === 'tab-published') {
            return [
              {
                text: 'Priority',
                value: 'priority',
                align: 'left',
                sortable: false,
              }, {
                text: 'Task',
                value: 'task',
                align: 'left',
              }, {
                text: 'Arguments',
                value: 'task_args',
                align: 'left',
              }, {
                text: 'Keyword arguments',
                value: 'content',
                align: 'left',
              },
            ]
          } else if (this.tabs === 'tab-failed') {
            return [
              {
                text: 'Failure time',
                value: 'failure_time',
                align: 'left',
              }, {
                text: 'Task',
                value: 'task',
                align: 'left',
              }, {
                text: 'Arguments',
                value: 'task_args',
                align: 'left',
              }, {
                text: 'Keyword arguments',
                value: 'content',
                align: 'left',
              }, {
                text: 'Exception',
                value: 'exception',
                align: 'left',
              }
            ]
          } else if (this.tabs === 'tab-completed') {
          return [
              {
                text: 'Completion time',
                value: 'completion_time',
                align: 'left',
              }, {
                text: 'Task',
                value: 'task',
                align: 'left',
              }, {
                text: 'Arguments',
                value: 'task_args',
                align: 'left',
              }, {
                text: 'Keyword arguments',
                value: 'content',
                align: 'left',
              }
            ]
          } else {
            return [
              {
                text: 'Task',
                value: 'task',
                align: 'left',
              }, {
                text: 'Interval',
                value: 'interval',
                align: 'left',
              }, {
                text: 'Active',
                value: 'active',
                align: 'left',
              },
            ]
          }
        }
      },
      data: {
        levels: [
            { value: 1, label: 'DEBUG'},
            { value: 2, label: 'INFO'},
            { value: 3, label: 'WARNING'},
            { value: 4, label: 'ERROR'},
            { value: 5, label: 'CRITICAL'},
        ],
        logLevel: 2,
        pagination: {},
        pageNumber: 1,
        pages: [
          { id: 'published', title: 'Queued' },
          { id: 'failed', title: 'Failed' },
          { id: 'completed', title: 'Completed' },
          { id: 'scheduled', title: 'Scheduled' }
        ],

        search: null,
        clipped: true,
        page: null,
        drawer: true,
        fixed: false,
        tabs: null,
        miniVariant: false,
        right: true,
        rightDrawer: false,
        title: 'django-carrot monitor',
        selectedMessageLog: null,
        displayMessageLog: false,

        displayScheduledTask: false,
        selectedScheduledTask: null,
        loading: false,
        errors: {},

        intervalTypes: [
            'seconds','minutes','hours','days'
        ],
        valid: null,
        required: [
          function (value) {
            if (value) {
                return !!value
            } else {
                return 'This field is required'
            }
          }
        ],
        requiredNumeric: [
            function (value) {
                if (Number.isInteger(parseInt(value))) {
                    return !!value
                } else {
                    return 'Please enter a valid number'
                }
            }
        ],
        validKeywords: [
            function (v) {
            if (v) {
                try {
                    JSON.parse(v)
                    return !!v
                } catch (e) {
                    return 'This is not valid JSON input'
                }
            }
            return true
            }
        ],
        positionalErrors: [],
      }
    })
  </script>
</body>
</html>
