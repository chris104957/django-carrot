Vue.component('task-detail', {
    delimiters: ['[[', ']]'],
    props: ['task', 'logLevel',],
    filters: {
        formatDate: function(rawDate) {
            // filter for converting a raw string to something more human-readable
            return moment(String(rawDate)).format('DD/MM/YYYY hh:mm')
        },
        cropped: function(data) {
            console.log(this.app.$options.filters.cropped);
            return this.app.$options.filters.cropped(data);
        },
        croppedKwargs: function(data) {
            return this.app.$options.filters.croppedKwargs(data);
        },
    },
    methods: {
        getIndent: function(line) {
            // calculates the indent_level class to apply to the LI elements in the traceback, eg class="indent_level_2"
            var level = (line.length - line.trim().length) / 2;
            return 'indent_level_' + level;
        },
        splitTraceback: function(rawTraceback) {
            return rawTraceback.split('\n');
        },
    },
    template: '{{ task_detail_template }}',
})


Vue.component('search-bar', {
    delimiters: ['[[', ']]'],
    props: ['queryset'],
    template: '{{ search_bar_template }}',
    data() {
        return {
            searchTerm: null,
        }
    },
    watch: {
        searchTerm: _.debounce(function() {
            this.$emit('callback', this.searchTerm)
        }, 500),
    }
})

Vue.component('scheduled-task', {
    delimiters: ['[[', ']]'],
    props: ['task', 'errors'],
    methods: {
        taskChoices: function() {
            return {{ task_options }}
        },
        intervalChoices: function() {
            return {{ interval_options }}
        },
        getClass: function(errors) {
            if (errors) {
                return 'error_td'
            }
        },
    },
    template: '{{ scheduled_task_template }}',
})

Vue.component('field-errors', {
    delimiters: ['[[', ']]'],
    props: ['errors'],
    template: '{{ field_errors }}'
})

Vue.component('icon', {
    delimiters: ['[[', ']]'],
    props: ['type'],
    template: '<i class="material-icons">[[ type ]]</i>'
})

Vue.component('paginator', {
    delimiters: ['[[', ']]'],
    props: ['type'],
    methods: {
        page: function() {
            return this.$parent.getPage(this.type)
        },
        pageCount: function() {
            return this.$parent.getPageCount(this.type)
        },
        setPage: function(newCount) {
            this.$parent.setPage(this.type, newCount)
        }
    },
    template: '{{ paginator_template }}'
})

var app = new Vue({
    el: '#app',
    delimiters: ['[[', ']]'],

    data: {
        selectedType: 'queued',
        highlightMode: false,
        selectedObjectId: null,
        selectedObject: null,
        logLevel: 'INFO',
        logLevels: [
            'DEBUG',
            'INFO',
            'WARNING',
            'ERROR',
            'CRITICAL'
        ],
        log : null,
        traceback : null,

        refreshInterval: 5,

        showSave: false,
        formErrors: {},

        selectedScheduledObjectId: null,
        selectedScheduledObject: null,

        publishedObjects: [],
        publishedPage: 1,
        publishedPageCount: 0,
        publishedPreviousPage: null,
        publishedNextPage: null,

        failedObjects: [],
        failedPage: 1,
        failedPageCount: 0,
        failedPreviousPage: null,
        failedNextPage: null,

        completedObjects: [],
        completedPage: 1,
        completedPageCount: 0,
        completedPreviousPage: null,
        completedNextPage: null,

        scheduledObjects: [],
        scheduledPage: 1,
        scheduledPageCount: 0,
        scheduledPreviousPage: null,
        scheduledNextPage: null,

        completedSearchTerm: null,
        failedSearchTerm: null,
        publishedSearchTerm: null,
    },
    created: function () {
        this.getPublishedMessageLogs()
        this.getFailedMessageLogs()
        this.getCompletedMessageLogs()
        this.getScheduledTasks()
    },
    mounted: function() {
        // carrot monitor calls getPublishedMessageLogs, getFailedMessageLogs, getCompletedMessageLogs periodically
        // to ensure that users can see tasks moving from the published to the failed/completed queues without having
        // to manually refresh the page every time.
        setInterval(function () {
            this.getPublishedMessageLogs();
            this.getFailedMessageLogs()
            this.getCompletedMessageLogs();
        }.bind(this), this.refreshInterval * 1000);

    },
    filters: {
        formatDate: function(rawDate) {
            // filter for converting a raw string to something more human-readable
            return moment(String(rawDate)).format('DD/MM/YYYY hh:mm')
        },
        cropped: function(task_args) {
            // crop the list of task arguments to a reasonable length
            var full = task_args.split(',');
            var cropped = full.slice(0, 10);

            if (full.length > cropped.length) {
                var diff = full.length - cropped.length;
                cropped.push('(' + diff + ' more items not displayed)')
            }
            return cropped.join(', ')
        },
        croppedKwargs: function(rawKwargs) {
            var obj = JSON.parse(rawKwargs)
            var count = 0;
            var value;
            var cleaned = {};
            for (var key in obj) {
                count = count + 1
                if (count > 10) {
                    break
                }
                value = obj[key]
                var maxLength;
                if (Array.isArray(value)) {
                    maxLength = 10;
                } else {
                    maxLength = 50;
                }

                if (value.length > maxLength) {
                    value = value.slice(0, maxLength) + '...'
                }
                cleaned[key] = value
            }

            return cleaned
        }
    },
    methods: {
        setLog: function() {
            // splits a task's traceback at the line breaks
            var self = this;
            if (self.selectedObject.log) {
                var rawLines = self.selectedObject.log.split('\n');
                var output = [];

                for (i = 0; i < rawLines.length; i ++) {
                    if (rawLines[i]) {
                        var splitLine = rawLines[i].split('::')
                        var preColon = splitLine[0].split(' ')
                        var message = splitLine[1]
                        var level = self.getLevel(preColon[3]);
                        if (level >= self.getLevel(self.logLevel)) {
                            var rowData = {
                                consumer: preColon[0],
                                date: preColon[1],
                                time: preColon[2],
                                level: preColon[3],
                                message: message,
                            };
                            output.push(rowData);
                        }
                    }
                };
                this.log = output;
            }
        },
        updateType(value) {
            this.selectedType = value
        },
        filterCompleted(searchTerm) {
            this.completedSearchTerm = searchTerm
            this.getCompletedMessageLogs()
        },
        filterPublished(searchTerm) {
            this.publishedSearchTerm = searchTerm
            this.getPublishedMessageLogs()
        },
        filterFailed(searchTerm) {
            this.failedSearchTerm = searchTerm
            this.getFailedMessageLogs()
        },
        // methods for calling the REST API
        getPublishedMessageLogs: function () {
            var self = this;
            if (this.publishedSearchTerm) {
                var url = '/carrot/api/message-logs/published/?page=' + self.publishedPage + '&search=' + this.publishedSearchTerm
            } else {
                var url = '/carrot/api/message-logs/published/?page=' + self.publishedPage
            }

            return axios.get(url)
            .then(function (response) {
                var count = response.data.count;
                var pages = parseInt(count/50);
                if (pages != count/50) {
                    pages = pages + 1;
                };
                self.publishedPreviousPage = response.data.previous;
                self.publishedPageCount = pages;
                self.publishedNextPage = response.data.next;
                self.publishedObjects = response.data.results
            })
            .catch(function (error) {
                console.log(error);
            })
        },
        getFailedMessageLogs: function () {
            var self = this;
            if (this.failedSearchTerm) {
                var url = '/carrot/api/message-logs/failed/?page=' + self.failedPage + '&search=' + this.failedSearchTerm
            } else {
                var url = '/carrot/api/message-logs/failed/?page=' + self.failedPage
            }

            return axios.get(url)
            .then(function (response) {
                var count = response.data.count;
                var pages = parseInt(count/50);
                if (pages != count/50) {
                    pages = pages + 1;
                };

                self.failedPreviousPage = response.data.previous;
                self.failedPageCount = pages;
                self.failedNextPage = response.data.next;
                self.failedObjects = response.data.results
            })
            .catch(function (error) {
                console.log(error);
            })
        },
        getCompletedMessageLogs: function () {
            var self = this;
            if (this.completedSearchTerm) {
                var url = '/carrot/api/message-logs/completed/?page=' + self.completedPage + '&search=' + this.completedSearchTerm
            } else {
                var url = '/carrot/api/message-logs/completed/?page=' + self.completedPage
            }
            console.log(url)

            return axios.get(url)
            .then(function (response) {
                var count = response.data.count;
                var pages = parseInt(count/50);
                if (pages != count/50) {
                    pages = pages + 1;
                };

                self.completedPreviousPage = response.data.previous;
                self.completedPageCount = pages;
                self.completedNextPage = response.data.next;
                self.completedObjects = response.data.results
            })
            .catch(function (error) {
                console.log(error);
            })
        },
        getScheduledTasks: function () {
            var self = this;
            return axios.get('/carrot/api/scheduled-tasks/?page=' + self.scheduledPage)
            .then(function (response) {
                var count = response.data.count;
                var pages = parseInt(count/50);
                if (pages != count/50) {
                    pages = pages + 1;
                };

                self.scheduledPreviousPage = response.data.previous;
                self.scheduledPageCount = pages;
                self.scheduledNextPage = response.data.next;
                self.scheduledObjects = response.data.results
            })
            .catch(function (error) {
                console.log(error);
            })
        },
        highlight: function(event) {
            window.scrollTo(0,0);
            var self = this;
            var elementId = event.target.parentElement.id;
            var taskId = elementId.split('_')[1];
            var overlay = document.getElementById('overlay');
            self.highlightMode = true;
            self.selectedObjectId = taskId;
        },
        highlightScheduled: function(event) {
            window.scrollTo(0,0);
            var self = this;
            var elementId = event.target.parentElement.id;
            var taskId = elementId.split('_')[1];
            var overlay = document.getElementById('overlay');
            self.highlightMode = true;
            self.selectedScheduledObjectId = taskId;
        },
        hideOverlay: function() {
            this.highlightMode = false;
            this.selectedObjectId = null;
            this.selectedObject = null;
            this.selectedScheduledObjectId = null;
            this.selectedScheduledObject = null;
            this.getScheduledTasks();
            this.formErrors = {};
            this.showSave = false;
        },
        getTask: function(taskId) {
            // returns the data for a single task object by calling the REST API
            var self = this;
            return axios.get('/carrot/api/message-logs/' + taskId + '/')
            .then(function (response) {
                self.selectedObject = response.data;
            })
            .catch(function (error) {
                console.log(error);
            })
        },
        getScheduledTask: function() {
            // returns the data for a single task object by calling the REST API
            var self = this;
            return axios.get('/carrot/api/scheduled-tasks/' + self.selectedScheduledObjectId + '/')
            .then(function (response) {
                self.selectedScheduledObject = response.data;
            })
            .catch(function (error) {
                console.log(error);
            })
        },
        getLevel: function(levelName) {
            // converts a level name to an int e.g. converts 'WARNING' to '3'
            var levels = {
                DEBUG: 1,
                INFO: 2,
                WARNING: 3,
                ERROR: 4,
                CRITICAL: 5
            };
            return levels[levelName];
        },
        requeueAll: function () {
            // calls the API that requeues ALL failed MessageLogs. On getting a success callback, getFailedMessageLogs
            // and getPublishedMessageLogs are called
            var self = this;
            self.failedObjects = []
            return axios.put('/carrot/api/message-logs/failed/', {},
                {
                    headers: {
                        'X-CSRFToken': '{{ csrf_token }}'
                    }
                }
            )
            .then(function (response) {
                console.log(response)
                self.getFailedMessageLogs()
                self.getPublishedMessageLogs()
            })
            .catch(function (error) {
                console.log(error);
            })
        },
        deleteAll: function () {
            // calls the API that deletes ALL failed MessageLogs. On getting a success callback, getFailedMessageLogs
            // is called
            var self = this;
            return axios.delete('/carrot/api/message-logs/failed/',
                {
                    headers: {
                        'X-CSRFToken': '{{ csrf_token }}'
                    }
                }
            )
            .then(function (response) {
                self.getFailedMessageLogs()
            })
            .catch(function (error) {
                console.log(error);
            })
        },
        requeueOne: function(objectPk) {
            // requeues a single task
            var self = this;
            return axios.put('/carrot/api/message-logs/' + objectPk + '/', {},
                {
                    headers: {
                        'X-CSRFToken': '{{ csrf_token }}'
                    }
                }
            )
            .then(function (response) {
                self.hideOverlay();
                self.getFailedMessageLogs();
                self.getPublishedMessageLogs();
            })
            .catch(function (error) {
                console.log(error);
            })
        },
        deleteOne: function(objectPk) {
            // deletes a single failed MessageLog objects
            var self = this;
            return axios.delete('/carrot/api/message-logs/' + objectPk + '/',
                {
                    headers: {
                        'X-CSRFToken': '{{ csrf_token }}'
                    }
                }
            )
            .then(function (response) {
                self.hideOverlay();
                self.getFailedMessageLogs()
            })
            .catch(function (error) {
                console.log(error);
                this.fetchError = error
            })
        },
        save: function(task) {
            // save a ScheduledTask object
            console.log(task);
            var self = this;
            this.formErrors = {};
            if (task.id) {
                return axios.patch('/carrot/api/scheduled-tasks/' + task.id + '/', task, {
                    headers: {
                        'X-CSRFToken': '{{ csrf_token }}'
                    }
                })
                .then(function (response) {
                    self.showSave = true;
                })
                .catch(function (error) {
                    var errors = error.response.data;
                    self.formErrors = errors;
                })
            } else {
                return axios.post('/carrot/api/scheduled-tasks/', task, {
                    headers: {
                        'X-CSRFToken': '{{ csrf_token }}'
                    }
                })
                .then(function (response) {
                    self.showSave = true;
                })
                .catch(function (error) {
                    var errors = error.response.data;
                    self.formErrors = errors;
                })
            }
        },
        runScheduledTask: function() {
            var self = this;
            if (self.selectedScheduledObject) {
                return axios.get('/carrot/api/scheduled-tasks/' + self.selectedScheduledObjectId + '/run/', {
                    headers: {
                        'X-CSRFToken': '{{ csrf_token }}'
                    }
                })
                .then(function (response) {
                    self.selectedScheduledObjectId = null;
                    self.getPublishedMessageLogs()
                    self.hideOverlay()
                })
                .catch(function (error) {
                    var errors = error.response.data;
                    console.log(errors);
                })
            }
        },
        deleteScheduledTask: function() {
            var self = this;
            if (self.selectedScheduledObject) {
                return axios.delete('/carrot/api/scheduled-tasks/' + self.selectedScheduledObjectId + '/', {
                    headers: {
                        'X-CSRFToken': '{{ csrf_token }}'
                    }
                })
                .then(function (response) {
                    self.selectedScheduledObjectId = null;
                    self.getScheduledTasks()
                    self.hideOverlay()
                })
                .catch(function (error) {
                    var errors = error.response.data;
                    console.log(errors);
                })
            }
        },
        hideSaveMsg: function () {
            this.showSave = false;
        },
        openCreateTaskForm: function() {
            var self = this;
            self.selectedScheduledObject = {};
            self.highlightMode = true;
            window.scrollTo(0,0);
        },
        isNotEmpty: function(dict) {
            if (Object.keys(dict).length == 0) {
                return false;
            };
            return true
        },
        // methods for setting and getting page numbers
        setPage: function(type, newPage) {
            var self = this;
            var attributeName = type + 'Page';
            Vue.set(self, attributeName, newPage);
        },
        getPage: function(type) {
            var self = this;
            var attributeName = type + 'Page';
            return self[attributeName];
        },
        getPageCount: function(type) {
            var self = this;
            var attributeName = type + 'PageCount';
            return self[attributeName];
        },
    }
})

// watchers that look for changes to the page numbers
app.$watch('publishedPage', function (newVal, oldVal) {
    app.getPublishedMessageLogs()
})

app.$watch('failedPage', function (newVal, oldVal) {
    app.getFailedMessageLogs()
})

app.$watch('completedPage', function (newVal, oldVal) {
    app.getCompletedMessageLogs()
})

app.$watch('scheduledPage', function (newVal, oldVal) {
    app.getScheduledTasks()
})

// watcher that calls app.getTask() whenever there is a change to the selected object pk, and that pk is not null
app.$watch('selectedObjectId', function (newVal, oldVal) {
    if (newVal) {
        app.getTask(newVal);
    }
})

// watch for changed to selectedScheduledObjectId and call getScheduledTask()
app.$watch('selectedScheduledObjectId', function (newVal, oldVal) {
    if (newVal) {
        app.getScheduledTask();
    }
})


// the next two watchers call setLog, which updates the app.log value from the selectedObject.log, on changes to the
// selectedObject or logLevel variables
app.$watch('selectedObject', function (newVal, oldVal) {
    if (newVal) {
        app.setLog();
    }
})

app.$watch('logLevel', function (newVal, oldVal) {
    if (newVal) {
        app.setLog();
    }
})


