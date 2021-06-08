
                                    README
------------------------------------------------------------------------------

Our system consists of three main modules that will be automatically used by 
the system in order to deploy and maintain an Health Monitoring System for 
Docker's containers:

    Antagonist:     a special container realized to test the software. 
                    it will shutdown containers or apply a packet loss
                    on the Docker host's containers. 
    
    DockerManager:  the system in duty of verifying the status of the
                    containers and eventually restore their functionalities
                    by a restart. It will also share information about the
                    containers in particular what containers are under 
                    management and their status
                    (ok/restarting, current packet loss)
                    
    Controller:     the element in charge of executing and maintains all 
                    the allocated DockerManagers. Its functionalities spread
                    from allocate DockerManager to maintain and verify their
                    status. Also it will implement a REST interface in order
                    to a user to manage the system, in particular to:
                    
                      - add new Docker host
                      - remove a Docker host
                      - verify the status of a single Docker host
                      - verify the status of all the Docker hosts
                      - modify the packet loss threshold of a DockerManager
                      - modify the packet loss threshold of all the managers
                        
The main module is the Controller one, that inside it stores all the
containers that it need to use(antagonist and DockerManager). In this way
we have a first big container capable of generating new containers and directly
allocate them inside the Docker hosts
                         
More information [WILL BE] available on the documentation
                                                    

